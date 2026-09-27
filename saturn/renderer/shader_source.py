"""Portable user fragment sources, includes and cached SPIR-V compilation."""
from __future__ import annotations
from functools import lru_cache
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile


class ShaderCompilationError(ValueError):
    """A user fragment could not be compiled for the selected GPU backend."""


_DECLARATION = re.compile(r"\buniform\s+(float|int|bool|vec[234])\s+([A-Za-z_]\w*)\s*;")
_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
_INCLUDE = re.compile(r'^\s*#include\s+["<]([^">]+)[">]\s*$', re.M)
_RESERVED = {"u_resolution", "u_time", "u_color", "u_secondary_color", "u_border_radius",
             "u_opacity", "iTime", "iResolution", "u_size", "u_transform", "u_buffer"}


def resolve_source(shader, includes=None, include_dirs=()):
    """Resolve explicitly supplied includes; report cycles and missing files."""
    directories = tuple(Path(p) for p in include_dirs)
    if isinstance(shader, Path):
        directories = (shader.resolve().parent, *directories)
        source = shader.read_text(encoding="utf-8")
    elif isinstance(shader, str):
        source = shader
    else:
        raise TypeError("shader must be a ShaderEffect, GLSL string, or pathlib.Path")
    snippets = dict(includes or {})
    def expand(text, dirs, chain=()):
        def include(match):
            name = match.group(1)
            if name in chain:
                raise ValueError("Cyclic shader include: " + " -> ".join((*chain, name)))
            if name in snippets:
                return expand(snippets[name], dirs, (*chain, name))
            for directory in dirs:
                file = directory / name
                if file.is_file():
                    return expand(file.read_text(encoding="utf-8"), (file.parent, *dirs), (*chain, name))
            raise FileNotFoundError(f"Shader include not found: {name}")
        return _INCLUDE.sub(include, text)
    return expand(source, directories)


def prepare_source(source, uniforms):
    """Extract scalar/vector uniforms and a portable mainImage entry point."""
    source = re.sub(r'^\s*#version[^\n]*', '', source, flags=re.M)
    clean = _COMMENT.sub('', source)
    if re.search(r'\bvoid\s+main\s*\(', clean):
        raise ValueError("User GLSL must define mainImage, not main; Saturn supplies the GPU entry point")
    declarations = {}
    for kind, name in _DECLARATION.findall(clean):
        if name in _RESERVED:
            raise ValueError(f"{name} is supplied by Saturn; remove its uniform declaration")
        if name in declarations:
            raise ValueError(f"Duplicate shader uniform: {name}")
        declarations[name] = kind
    clean = _DECLARATION.sub('', clean)
    if re.search(r'\buniform\b', clean):
        raise ValueError("Custom uniforms support float, int, bool and vec2/vec3/vec4; arrays, matrices and samplers are not supported")
    # Without a declaration numeric Python values become float uniforms.
    for name, value in uniforms.items():
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_]\w*', name) or name in _RESERVED:
            raise ValueError(f"Invalid or reserved shader uniform: {name!r}")
        if name not in declarations:
            declarations[name] = ('bool' if isinstance(value, bool) else
                                  f'vec{len(value)}' if isinstance(value, (tuple, list)) else 'float')
    layout = tuple(sorted(declarations.items()))
    if len(layout) > 252:
        raise ValueError("A custom shader supports at most 252 scalar/vector uniforms")
    values = []
    for name, kind in layout:
        count = int(kind[-1]) if kind.startswith('vec') else 1
        if kind not in ('float', 'int', 'bool', 'vec2', 'vec3', 'vec4'):
            raise ValueError(f"Unsupported shader uniform type for {name}: {kind}")
        value = uniforms.get(name, (0.0,)*count if count>1 else False if kind=='bool' else 0)
        if count > 1:
            if not isinstance(value, (tuple, list)) or len(value) != count:
                raise ValueError(f"{name} requires {count} numeric components")
            value = tuple(float(v) for v in value)
        elif kind == 'bool':
            if not isinstance(value, bool):
                raise TypeError(f"{name} requires a bool")
        elif kind == 'int':
            if isinstance(value, bool) or not isinstance(value, int) or not -(2**31)<=value<2**31:
                raise TypeError(f"{name} requires a signed 32-bit int")
        else:
            value = float(value)
        components = value if count > 1 else (value,)
        if not all(math.isfinite(v) for v in components):
            raise ValueError(f"{name} must be finite")
        values.append(value)
    body = _DECLARATION.sub('', source)
    if re.search(r'\bvec4\s+mainImage\s*\(\s*(?:in\s+)?vec2\b', clean):
        call = 'vec4 result = mainImage(v_uv);'
    elif re.search(r'\bvoid\s+mainImage\s*\(\s*out\s+vec4\b', clean):
        call = 'vec4 result; mainImage(result, v_uv * u_resolution);'
    else:
        raise ValueError("Define vec4 mainImage(vec2 uv), or void mainImage(out vec4 color, in vec2 pixel)")
    return body, layout, tuple(values), call


_TAIL = """
void main() {
    SATURN_CALL
    vec2 q = abs(v_uv * u_resolution - u_resolution * 0.5) -
             u_resolution * 0.5 + min(u_border_radius, min(u_resolution.x, u_resolution.y)*0.5);
    float d = min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) -
              min(u_border_radius, min(u_resolution.x, u_resolution.y)*0.5);
    float mask = 1.0 - smoothstep(-max(fwidth(d), 0.001), max(fwidth(d), 0.001), d);
    frag = vec4(result.rgb, result.a * mask * u_opacity);
}
"""


def fragment_source(body, layout, call, *, vulkan=False):
    if vulkan:
        header = '#version 450\nlayout(location=0) in vec2 v_uv;\nlayout(location=0) out vec4 frag;\n'
        header += 'layout(std140,set=1,binding=0) uniform SaturnUniforms { vec4 core[4]; vec4 user_values['+str(max(1,len(layout)))+']; } _saturn;\n'
        header += '\n'.join(('#define u_resolution _saturn.core[0].xy', '#define u_time _saturn.core[0].z',
                             '#define u_border_radius _saturn.core[0].w', '#define u_color _saturn.core[1]',
                             '#define u_secondary_color _saturn.core[2]', '#define u_opacity _saturn.core[3].x'))+'\n'
        for index, (name, kind) in enumerate(layout):
            value = f'_saturn.user_values[{index}]'
            expr = f'floatBitsToInt({value}.x)' if kind=='int' else f'({value}.x != 0.0)' if kind=='bool' else value+'.'+{'float':'x','vec2':'xy','vec3':'xyz','vec4':'xyzw'}[kind]
            header += f'#define {name} ({expr})\n'
    else:
        header = '#version 330\nin vec2 v_uv;\nout vec4 frag;\n'
        header += 'uniform vec2 u_resolution; uniform float u_time, u_border_radius, u_opacity;\nuniform vec4 u_color, u_secondary_color;\n'
        header += '\n'.join(f'uniform {kind} {name};' for name,kind in layout)+'\n'
    header += '#define iTime u_time\n#define iResolution vec3(u_resolution, 1.0)\n'
    if 'saturnSampleBuffer' in body:
        header += ('layout(set=0,binding=0) uniform sampler2D u_buffer;\n' if vulkan else
                   'uniform sampler2D u_buffer;\n')
        uv = 'uv' if vulkan else 'vec2(uv.x,1.0-uv.y)'
        header += f'vec4 saturnSampleBuffer(vec2 uv) {{ return textureLod(u_buffer,{uv},0.0); }}\n'
    return header+body+_TAIL.replace('SATURN_CALL', call)


def buffer_source(source, layout, *, vertex=False, vulkan=False):
    """One optional additive GPU buffer, sharing the fragment's uniform layout."""
    header = fragment_source('', layout, '', vulkan=vulkan).split('void main()')[0]
    header = re.sub(r'(?:layout\(location=0\) )?(?:in vec2 v_uv|out vec4 frag);\n', '', header)
    if vulkan:
        header = re.sub(r'#define u_opacity[^\n]*', '#define u_opacity 1.0', header)
        header = re.sub(r'#define u_border_radius[^\n]*', '#define u_border_radius 0.0', header)
    else:
        header += '#define u_opacity 1.0\n#define u_border_radius 0.0\n'
    header += ('#define SATURN_VULKAN 1\n#define SATURN_LOCATION(n) layout(location=n)\n'
               '#define SATURN_VERTEX_ID gl_VertexIndex\n#define SATURN_INSTANCE_ID gl_InstanceIndex\n'
               if vulkan else '#define SATURN_LOCATION(n)\n#define SATURN_VERTEX_ID gl_VertexID\n#define SATURN_INSTANCE_ID gl_InstanceID\n')
    return header + _DECLARATION.sub('', re.sub(r'^\s*#version[^\n]*', '', source, flags=re.M))


def pack_uniforms(layout, values, size, elapsed, radius, color, secondary, opacity):
    data = bytearray(struct.pack('16f', *size, elapsed, radius, *color, *secondary, opacity, 0, 0, 0))
    for (_,kind), value in zip(layout, values):
        if kind=='int':
            data.extend(struct.pack('i3f', value, 0, 0, 0))
        else:
            parts = value if isinstance(value, tuple) else (float(value),)
            data.extend(struct.pack('4f', *parts, *([0]*(4-len(parts)))))
    if not layout:
        data.extend(bytes(16))
    return bytes(data)


@lru_cache(maxsize=64)
def compile_spirv(source, stage='frag'):
    compiler = os.environ.get('SATURN_GLSLANG') or shutil.which('glslangValidator') or shutil.which('glslang')
    if not compiler and os.environ.get('VULKAN_SDK'):
        compiler = str(Path(os.environ['VULKAN_SDK'])/'Bin'/'glslangValidator.exe')
    if not compiler:
        raise ShaderCompilationError("Custom Vulkan GLSL requires glslangValidator on PATH or SATURN_GLSLANG set to its executable. Built-in effects do not require it.")
    with tempfile.TemporaryDirectory(prefix='saturn-glsl-') as directory:
        src, dst = Path(directory)/('effect.'+stage), Path(directory)/'effect.spv'
        src.write_text(source, encoding='utf-8')
        result = subprocess.run([compiler, '-V', '-S', stage, '-o', str(dst), str(src)],
                                capture_output=True, text=True, timeout=30,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise ShaderCompilationError((result.stdout+'\n'+result.stderr).strip())
        return dst.read_bytes()
