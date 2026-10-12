# Animation and Render Backends

Saturn animations can be described with animate_* properties, or by using the built-in state animations of
controls and Expressive controls. The drawing backend is chosen by the backend parameter of saturn.run.

## Property animation

Controls support animation configuration for opacity, size, position, align, margin, rotation, scale, and offset:

~~~python
panel = saturn.Container(
    saturn.Text("Animated"),
    width=240,
    height=120,
    bgcolor=saturn.Colors.PRIMARY_CONTAINER,
    animate_opacity=saturn.Animation(
        duration=saturn.Duration(milliseconds=250),
        curve=saturn.AnimationCurve.EASE_OUT,
    ),
)
page.add(panel)

panel.opacity = 0.3
panel.update()
~~~

The animation happens after the target value changes. Duration can use fields such as milliseconds and seconds;
AnimationCurve determines the interpolation speed. on_animation_end can be used after the animation completes.

Rotation, scale, and offset affect both drawing and hit testing, unless the corresponding type disables
transform_hit_tests. GPU rotation clipping uses conservative axis-aligned bounds.

## Choosing a backend

~~~python
saturn.run(main, backend=saturn.Renderer.SOFTWARE)
saturn.run(main, backend=saturn.Renderer.OPENGL)
saturn.run(main, backend=saturn.Renderer.VULKAN)
~~~

OpenGL is the GPU backend with the most complete support; Software is convenient when running without a GPU or when stable diagnostics are needed;
Vulkan is still an experimental backend. The backend actually in use is read from
page.renderer.name:

~~~python
def main(page):
    print(page.renderer.name)
~~~

renderer.anti_aliasing and renderer.vsync are both boolean settings, enabled by default. Changing them
is queued to the UI thread and may trigger re-layout or swap chain recreation.

## GPU selection and fallback

~~~python
saturn.run(main, backend=saturn.Renderer.VULKAN, gpu="Intel")
saturn.run(main, backend=saturn.Renderer.VULKAN, gpu=1)
~~~

gpu can be a device name, a unique substring, or an index. The actual device is read from gpu_name, gpu_index, and
gpus. When the selection is invalid or initialization fails, the application may fall back to the software backend:

~~~python
def report(event):
    print(event.backend, event.error)


page.on_render_failed = report
page.on_render_ready = lambda event: print(event.backend, event.fallback)
~~~

Fallback is a startup recovery mechanism; it will not replace an already-failed shader or arbitrary draw
calls at runtime. The application should prepare visible fallback behavior for the Software backend.

## Shaders

A Shader can use the built-in ShaderEffect, or pass a GLSL string or a Path. The GPU backend
executes the custom fragment; the Software backend draws fallback_color. For detailed uniform, include,
buffer, and error handling, see the [shader chapter](../shaders.md).

## Key points of this chapter

Animations change control state, and the renderer decides how that state is drawn. Validate layout
and events with Software first, then validate GPU effects with OpenGL or Vulkan. Do not treat the UI thread as a thread for time-consuming computation.
