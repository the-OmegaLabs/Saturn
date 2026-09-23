# Renderer

Selects the software, OpenGL, or Vulkan rendering backend.

[← API index](./README.md)

Source: [`saturn/app.py`](../../saturn/app.py) (line 30).

**Base class:** `Enum`

## Members

| Name | Value |
| --- | --- |
| `SOFTWARE` | `software` |
| `OPENGL` | `opengl` |
| `VULKAN` | `vulkan` |

`saturn.Renderer.OPENGL` and `saturn.Renderer.VULKAN` draw shapes on the GPU. Vulkan batches consecutive draw calls, clips them with the GPU scissor, and composites uploaded text and image textures in its graphics pipeline. It uses 4× MSAA when supported, falls back to 2× or 1× on other devices, and also smooths rounded shapes in the shader. Diagonal line and arc edges may remain jagged on devices limited to 1× sampling. Text and some effects are still prepared as surfaces before upload; the complete frame is not rasterized on the CPU. On supported surfaces, Vulkan screenshots read back the rendered GPU image. `saturn.Render` remains a compatibility alias.
