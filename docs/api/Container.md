# Container

Adds spacing, background, borders, and other decoration to a child.

[← API index](./README.md)

Source: [`saturn/widgets/containers.py`](../../saturn/widgets/containers.py) (line 326).

## Preview

![Container control in the dark theme](../../.static/controls/Container.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.window.width = 720
    page.window.height = 360
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Container(saturn.Text("A decorated container"), padding=24, bgcolor=saturn.Colors.PRIMARY_CONTAINER, border_radius=16))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.Container(content=None, *, padding=None, bgcolor=None, border=None, border_radius=None, alignment=None, gradient=None, shadow=None, ink=False, animate=None, on_click=None, on_hover=None, on_long_press=None, on_tap_down=None, ink_color=None, clip_behavior=None, shape='rectangle', url=None, ignore_interactions=False, blend_mode=None, image=None, blur=None, theme=None, dark_theme=None, theme_mode=None, color_filter=None, foreground_decoration=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `content` | `—` | `None` | Text or child control to display. |
| `padding` | `—` | `None` | Space around the control's content. |
| `bgcolor` | `—` | `None` | Background color of the control or container. |
| `border` | `—` | `None` | Border settings. |
| `border_radius` | `—` | `None` | Corner radius of the border or background. |
| `alignment` | `—` | `None` | Alignment of content inside the container. |
| `gradient` | `—` | `None` | Gradient used to fill the background. |
| `shadow` | `—` | `None` | Shadow outside the control. |
| `ink` | `—` | `False` | Whether to draw ripple feedback on clicks. |
| `animate` | `—` | `None` | Animation settings applied when a property changes. |
| `on_click` | `—` | `None` | Callback called when the control is clicked. |
| `on_hover` | `—` | `None` | Callback called when the pointer's hover state changes. |
| `on_long_press` | `—` | `None` | Callback called when the control is long pressed. |
| `on_tap_down` | `—` | `None` | Callback called when a press begins. |
| `ink_color` | `—` | `None` | Color for ink. |
| `clip_behavior` | `—` | `None` | Clip mode; GPU rotated clips use conservative axis-aligned bounds. |
| `shape` | `—` | `'rectangle'` | Base shape of the button. |
| `url` | `—` | `None` | Destination opened when the button is clicked. |
| `ignore_interactions` | `—` | `False` | Disable Slider interaction without changing appearance. |
| `blend_mode` | `—` | `None` | Unsupported for non-default requests. Requested blend mode option; see the control comparison for supported values and restrictions. |
| `image` | `—` | `None` | Unsupported for non-default requests. Requested image option; see the control comparison for supported values and restrictions. |
| `blur` | `—` | `None` | Backdrop Gaussian blur under this container (number, (sigma_x, sigma_y), or Blur). |
| `theme` | `—` | `None` | Unsupported for non-default requests. Light theme configuration. |
| `dark_theme` | `—` | `None` | Unsupported for non-default requests. Dark theme configuration. |
| `theme_mode` | `—` | `None` | Unsupported for non-default requests. Light, dark, or detected system preference. |
| `color_filter` | `—` | `None` | Unsupported for non-default requests. Requested color filter option; see the control comparison for supported values and restrictions. |
| `foreground_decoration` | `—` | `None` | Unsupported for non-default requests. Requested foreground decoration option; see the control comparison for supported values and restrictions. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
