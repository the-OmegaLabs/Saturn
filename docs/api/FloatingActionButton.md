# FloatingActionButton

Floating button that highlights a page's primary action.

[← API index](./README.md)

Source: [`saturn/widgets/fab.py`](../../saturn/widgets/fab.py) (line 26).

## Preview

![FloatingActionButton control in the dark theme](../../.static/controls/FloatingActionButton.png)

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
    page.add(saturn.FloatingActionButton(saturn.Icons.ADD))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE)
```

**Base class:** `_ConcreteButton`

## Constructor parameters

```python
saturn.FloatingActionButton(icon=None, *, content: 'str | None' = None, text: 'str | None' = None, mini: 'bool' = False, size: 'str' = 'standard', expanded: 'bool' = True, bgcolor=None, color=None, foreground_color=None, elevation: 'float' = 6.0, on_click=None, on_hover=None, shape=None, autofocus=False, focus_color=None, disabled_elevation=None, focus_elevation=None, highlight_elevation=None, hover_elevation=None, hover_color=None, splash_color=None, enable_feedback=None, url=None, mouse_cursor=None, clip_behavior='none', **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `icon` | `—` | `None` | Icon to draw. |
| `content` | `str | None` | `None` | Text or child control to display. |
| `text` | `str | None` | `None` | Text displayed on the control. |
| `mini` | `bool` | `False` | Use the small floating action button size. |
| `size` | `str` | `'standard'` | Size of the text, icon, or control. |
| `expanded` | `bool` | `True` | Whether the floating component or menu is expanded. |
| `bgcolor` | `—` | `None` | Background color of the control or container. |
| `color` | `—` | `None` | Color of foreground content, text, or drawing. |
| `foreground_color` | `—` | `None` | Foreground color of the floating action button. |
| `elevation` | `float` | `6.0` | Surface elevation, which determines shadow strength. |
| `on_click` | `—` | `None` | Callback called when the control is clicked. |
| `on_hover` | `—` | `None` | Callback called when the pointer's hover state changes. |
| `shape` | `—` | `None` | Base shape of the button. |
| `autofocus` | `—` | `False` | Try to focus this control when the page opens. |
| `focus_color` | `—` | `None` | Color for focus. |
| `disabled_elevation` | `—` | `None` | Shadow elevation during disabled. |
| `focus_elevation` | `—` | `None` | Shadow elevation during focus. |
| `highlight_elevation` | `—` | `None` | Shadow elevation during highlight. |
| `hover_elevation` | `—` | `None` | Shadow elevation during hover. |
| `hover_color` | `—` | `None` | Color used in the hover state. |
| `splash_color` | `—` | `None` | Color for splash. |
| `enable_feedback` | `—` | `None` | Unsupported for non-default requests. Provide interaction feedback when enabled. |
| `url` | `—` | `None` | Destination opened when the button is clicked. |
| `mouse_cursor` | `—` | `None` | Cursor displayed while hovering over the control. |
| `clip_behavior` | `—` | `'none'` | Clip mode; GPU rotated clips use conservative axis-aligned bounds. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
