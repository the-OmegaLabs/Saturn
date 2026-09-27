# Shader

Built-in effects or custom GLSL fragment backgrounds on OpenGL and Vulkan; see the Shader guide.

[← API index](./README.md)

Source: [`saturn/widgets/shader.py`](../../saturn/widgets/shader.py) (line 32).

**Base class:** [Control](./Control.md)

## Public methods

| Method | Description |
| --- | --- |
| `reload(self)` | Read the source file and includes again on the next frame. |

## Constructor parameters

```python
saturn.Shader(effect: 'ShaderEffect | str | None' = None, *, shader=None, color='#6750A4', secondary_color='#EADDFF', uniforms=None, animate: 'bool' = True, speed: 'float' = 1.0, time: 'float' = 0.0, border_radius: 'float' = 0.0, fallback_color=None, includes=None, include_dirs=(), on_error=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `effect` | `ShaderEffect | str | None` | `None` | Compatibility alias for shader; pass only one of them. |
| `shader` | `—` | `None` | ShaderEffect, GLSL source string, or pathlib.Path to a fragment source file. |
| `color` | `—` | `'#6750A4'` | Color of foreground content, text, or drawing. |
| `secondary_color` | `—` | `'#EADDFF'` | Color for secondary. |
| `uniforms` | `—` | `None` | Built-in effect parameters or custom GLSL scalar/vector uniform values. |
| `animate` | `bool` | `True` | Request frames to advance time while visible on a GPU backend. |
| `speed` | `float` | `1.0` | Multiplier for elapsed Shader animation time. |
| `time` | `float` | `0.0` | Shader time offset in seconds. |
| `border_radius` | `float` | `0.0` | Corner radius of the border or background. |
| `fallback_color` | `—` | `None` | Static fill used by the software backend. |
| `includes` | `—` | `None` | Mapping from include names to GLSL snippets. |
| `include_dirs` | `—` | `()` | Explicit folders searched for GLSL include files. |
| `on_error` | `—` | `None` | Callback for error; accepts zero arguments or an event. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
