"""Windows OpenGL GPU binding, using vendor affinity/association extensions.

Selected-device frames remain on the GPU: NVIDIA copies between contexts;
AMD blits between contexts. Drivers without these extensions expose their
current adapter and reject unsupported explicit requests.
"""
import ctypes as C
import sys
from .gpu import GPUSelectionError, normalized_name, select_gpu

P, U, I = C.c_void_p, C.c_uint, C.c_int


class _Rect(C.Structure):
    _fields_ = [('left',I),('top',I),('right',I),('bottom',I)]


class _GPUDevice(C.Structure):
    _fields_ = [('size',U),('device',C.c_char*32),('name',C.c_char*128),('flags',U),('rect',_Rect)]


class _PixelFormat(C.Structure):
    _fields_ = [('size',C.c_ushort),('version',C.c_ushort),('flags',U),
        *[(name,C.c_ubyte) for name in ('pixelType','colorBits','redBits','redShift','greenBits',
        'greenShift','blueBits','blueShift','alphaBits','alphaShift','accumBits','accumRedBits',
        'accumGreenBits','accumBlueBits','accumAlphaBits','depthBits','stencilBits','auxBuffers',
        'layerType','reserved')],('layerMask',U),('visibleMask',U),('damageMask',U)]


class GLGPUBinding:
    def __init__(self, context, gpu):
        self.default_context = context
        self.current_name = context.info['GL_RENDERER']
        self.names = (self.current_name,)
        self.index = 0
        self.render_rc = self.render_dc = None
        self.kind = None
        self._texture = self._program = self._vao = None
        self._size = None
        if sys.platform != 'win32':
            self.index = select_gpu(self.names, gpu)
            return
        self.gl = C.WinDLL('opengl32.dll',use_last_error=True)
        for name, result, args in (
            ('wglGetProcAddress',P,[C.c_char_p]),('wglGetCurrentContext',P,[]),
            ('wglGetCurrentDC',P,[]),('wglMakeCurrent',I,[P,P]),
            ('wglDeleteContext',I,[P]),('wglCreateContext',P,[P]),
            ('glFlush',None,[])):
            fn = getattr(self.gl,name)
            fn.restype, fn.argtypes = result,args
        self.default_rc, self.default_dc = self.gl.wglGetCurrentContext(),self.gl.wglGetCurrentDC()
        query = self.function('wglGetExtensionsStringARB',C.c_char_p,P)
        extensions = (query(self.default_dc) or b'').decode('ascii').split() if query else ()
        devices = []
        if 'WGL_NV_gpu_affinity' in extensions:
            enum = self.function('wglEnumGpusNV',I,U,C.POINTER(P))
            detail = self.function('wglEnumGpuDevicesNV',I,P,U,C.POINTER(_GPUDevice))
            if enum and detail:
                for index in range(256):
                    handle = P()
                    if not enum(index,C.byref(handle)):
                        break
                    item = _GPUDevice()
                    item.size = C.sizeof(item)
                    name = item.name.decode('utf-8',errors='replace') if detail(handle,0,C.byref(item)) else f'OpenGL GPU {index}'
                    devices.append((handle.value,name))
                if devices:
                    self.kind = 'nv'
        if not devices and 'WGL_AMD_gpu_association' in extensions:
            enum = self.function('wglGetGPUIDsAMD',U,U,C.POINTER(U))
            detail = self.function('wglGetGPUInfoAMD',I,U,I,U,U,P)
            if enum and detail:
                count = enum(0,None)
                if count>256:
                    raise GPUSelectionError('OpenGL driver returned an invalid GPU count')
                ids = (U*count)()
                enum(count,ids)
                for identifier in ids:
                    buf = C.create_string_buffer(1024)
                    if detail(identifier,0x1F01,0x1401,len(buf),buf)>0:
                        devices.append((identifier,buf.value.decode('utf-8',errors='replace')))
                if devices:
                    self.kind = 'amd'
        if not devices:
            try:
                self.index = select_gpu(self.names,gpu)
            except GPUSelectionError as error:
                raise GPUSelectionError(f'{error}. This OpenGL driver does not expose GPU affinity/association; '
                    'use a supported driver, configure the OS graphics preference, or select Vulkan.') from error
            return
        self.names = tuple(name for _,name in devices)
        matches = [i for i,name in enumerate(self.names) if normalized_name(name)==normalized_name(self.current_name)]
        default = matches[0] if len(matches)==1 else None
        if self.kind=='amd':
            current = self.function('wglGetContextGPUIDAMD',U,P)
            identifier = current(self.default_rc) if current else 0
            default = next((i for i,(handle,_) in enumerate(devices) if handle==identifier),default)
        self.index = select_gpu(self.names,gpu,default) if gpu is not None else default
        if gpu is None or self.index==default:
            return
        try:
            self._create(devices[self.index][0])
        except Exception:
            self.close()
            raise

    def function(self, name, result, *args):
        address = self.gl.wglGetProcAddress(name.encode('ascii'))
        if address in (None,0,1,2,3,P(-1).value):
            return None
        return C.WINFUNCTYPE(result,*args)(address)

    def load_opengl_function(self, name):
        address = self.gl.wglGetProcAddress(name.encode('ascii'))
        if address not in (None,0,1,2,3,P(-1).value):
            return address
        return C.cast(getattr(self.gl,name,None),P).value or 0

    def __enter__(self):
        self.activate()

    def __exit__(self,*args):
        pass

    def release(self):
        # ModernGL releases its wrapper before the explicit native cleanup.
        pass

    def _create(self, identifier):
        attrs = (I*7)(0x2091,3,0x2092,3,0x9126,1,0)
        if self.kind=='nv':
            self._copy = self.function('wglCopyImageSubDataNV',I,P,U,U,I,I,I,I,P,U,U,I,I,I,I,I,I,I)
            self._delete_dc = self.function('wglDeleteDCNV',I,P)
            create_dc = self.function('wglCreateAffinityDCNV',P,C.POINTER(P))
            if not (self._copy and self._delete_dc and create_dc):
                raise GPUSelectionError('NVIDIA OpenGL selection requires GPU affinity and cross-context GPU copy support')
            self.render_dc = create_dc((P*2)(identifier,None))
            if not self.render_dc:
                raise GPUSelectionError('Cannot create the requested NVIDIA GPU affinity DC')
            gdi = C.WinDLL('gdi32.dll',use_last_error=True)
            for name,result,args in (('GetPixelFormat',I,[P]),
                ('DescribePixelFormat',I,[P,I,U,C.POINTER(_PixelFormat)]),
                ('ChoosePixelFormat',I,[P,C.POINTER(_PixelFormat)]),
                ('SetPixelFormat',I,[P,I,C.POINTER(_PixelFormat)])):
                fn = getattr(gdi,name)
                fn.restype,fn.argtypes=result,args
            pixel = _PixelFormat()
            if not gdi.DescribePixelFormat(self.default_dc,gdi.GetPixelFormat(self.default_dc),C.sizeof(pixel),C.byref(pixel)):
                raise GPUSelectionError('Cannot inspect the window OpenGL pixel format')
            format = gdi.ChoosePixelFormat(self.render_dc,C.byref(pixel))
            if not format or not gdi.SetPixelFormat(self.render_dc,format,C.byref(pixel)):
                raise GPUSelectionError('Cannot initialize the requested GPU pixel format')
            create = self.function('wglCreateContextAttribsARB',P,P,P,C.POINTER(I))
            self.render_rc = create(self.render_dc,None,attrs) if create else self.gl.wglCreateContext(self.render_dc)
        else:
            self._make = self.function('wglMakeAssociatedContextCurrentAMD',I,P)
            self._current = self.function('wglGetCurrentAssociatedContextAMD',P)
            self._delete = self.function('wglDeleteAssociatedContextAMD',I,P)
            create = self.function('wglCreateAssociatedContextAttribsAMD',P,U,P,C.POINTER(I))
            fallback = self.function('wglCreateAssociatedContextAMD',P,U)
            if not (self._make and self._current and self._delete and (create or fallback)):
                raise GPUSelectionError('AMD OpenGL GPU association is incomplete')
            self.render_rc = create(identifier,None,attrs) if create else fallback(identifier)
        if not self.render_rc:
            raise GPUSelectionError('The driver could not create a context on the requested GPU')
        self.activate()
        if self.kind=='nv':
            enum = self.function('wglEnumGpusFromAffinityDCNV',I,P,U,C.POINTER(P))
            actual = P()
            if not enum or not enum(self.render_dc,0,C.byref(actual)) or actual.value!=identifier:
                raise GPUSelectionError('The NVIDIA context did not bind the requested GPU')
        else:
            query = self.function('wglGetContextGPUIDAMD',U,P)
            if not query or query(self.render_rc)!=identifier:
                raise GPUSelectionError('The AMD context did not bind the requested GPU')
            self._blit = self.function('wglBlitContextFramebufferAMD',None,P,I,I,I,I,I,I,I,I,U,U)
            if not self._blit:
                raise GPUSelectionError('AMD GPU presentation requires cross-context framebuffer blit support')

    def activate_default(self):
        if self.gl.wglGetCurrentContext()!=self.default_rc:
            if not self.gl.wglMakeCurrent(self.default_dc,self.default_rc):
                raise GPUSelectionError('Cannot activate the window OpenGL context')

    def activate(self):
        if not self.render_rc:
            self.activate_default()
        elif self.kind=='nv':
            if self.gl.wglGetCurrentContext()!=self.render_rc and not self.gl.wglMakeCurrent(self.render_dc,self.render_rc):
                raise GPUSelectionError('Cannot activate the selected NVIDIA GPU')
        elif self._current()!=self.render_rc and not self._make(self.render_rc):
            raise GPUSelectionError('Cannot activate the selected AMD GPU')

    def present(self, frame, color, pixel_size, render_context):
        import moderngl as gl
        source_size = color.size
        try:
            if self.kind=='amd':
                self.activate_default()
                self.default_context.screen.use()
                self.default_context.scissor=None
                self.activate()
                frame.use()
                render_context.scissor=None
                self._blit(self.default_rc,0,0,*source_size,0,0,*pixel_size,0x4000,0x2601)
                if render_context.error!='GL_NO_ERROR':
                    raise GPUSelectionError('AMD GPU framebuffer presentation failed')
                self.activate_default()
                return
            self.activate_default()
            ctx=self.default_context
            if self._program is None:
                self._program=ctx.program(vertex_shader='''#version 330
                    out vec2 uv; void main() { vec2 p=vec2((gl_VertexID==1)?3.0:-1.0,(gl_VertexID==2)?3.0:-1.0);
                    uv=(p+1.0)*.5; gl_Position=vec4(p,0,1); }''',
                    fragment_shader='''#version 330
                    uniform sampler2D image; in vec2 uv; out vec4 color;
                    void main(){color=texture(image,uv);}''')
                self._vao=ctx.vertex_array(self._program,[])
                self._program['image'].value=0
            if self._size!=source_size:
                if self._texture is not None:
                    self._texture.release()
                self._texture=ctx.texture(source_size,4)
                self._texture.filter=(gl.LINEAR,gl.LINEAR)
                self._texture.repeat_x=self._texture.repeat_y=False
                self._size=source_size
            self.activate()
            # Ensure source commands are submitted before the cross-context copy.
            self.gl.glFlush()
            if not self._copy(self.render_rc,color.glo,0x0DE1,0,0,0,0,
                self.default_rc,self._texture.glo,0x0DE1,0,0,0,0,*source_size,1):
                raise GPUSelectionError('NVIDIA cross-context GPU image copy failed')
            self.activate_default()
            ctx.screen.use()
            ctx.viewport=(0,0,*pixel_size)
            ctx.scissor=None
            ctx.disable(gl.BLEND)
            self._texture.use(0)
            self._vao.render(gl.TRIANGLES,vertices=3)
        except Exception:
            self.activate()
            raise

    def close(self):
        if not hasattr(self,'gl'):
            return
        self.activate_default()
        for resource in (self._vao,self._program,self._texture):
            if resource is not None:
                resource.release()
        if self.render_rc:
            if self.kind=='nv':
                self.gl.wglDeleteContext(self.render_rc)
            else:
                self._delete(self.render_rc)
            self.render_rc=None
        if self.render_dc:
            self._delete_dc(self.render_dc)
            self.render_dc=None
