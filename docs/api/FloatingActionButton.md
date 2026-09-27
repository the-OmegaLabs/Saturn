# FloatingActionButton

Floating button that highlights a page's primary action.

[← API index](./README.md)

Source: [`saturn/widgets/fab.py`](../../saturn/widgets/fab.py) (line 24).

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
saturn.FloatingActionButton(icon=None, *, content: 'str | None' = None, text: 'str | None' = None, mini: 'bool' = False, size: 'str' = 'standard', expanded: 'bool' = True, bgcolor=None, color=None, foreground_color=None, elevation: 'float' = 6.0, on_click=None, on_hover=None, **base)
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
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
