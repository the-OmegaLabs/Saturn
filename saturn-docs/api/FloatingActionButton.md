# FloatingActionButton

Floating button that highlights a page's primary action.

[← API index](./README.md)

Source: [`saturn/widgets/fab.py`](../../saturn/widgets/fab.py) (line 24).

## Preview

![FloatingActionButton control in the dark theme](../images/controls/FloatingActionButton.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.FloatingActionButton(saturn.Icons.ADD))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** `_ConcreteButton`

## Constructor parameters

```python
saturn.FloatingActionButton(icon=None, *, text: 'str | None' = None, size: 'str' = 'standard', expanded: 'bool' = True, bgcolor=None, color=None, elevation: 'float' = 6.0, on_click=None, on_hover=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `icon` | `—` | `None` | Icon to draw. |
| `text` | `str | None` | `None` | Text displayed on the control. |
| `size` | `str` | `'standard'` | Size of the text, icon, or control. |
| `expanded` | `bool` | `True` | Whether the floating component or menu is expanded. |
| `bgcolor` | `—` | `None` | Background color of the control or container. |
| `color` | `—` | `None` | Color of foreground content, text, or drawing. |
| `elevation` | `float` | `6.0` | Surface elevation, which determines shadow strength. |
| `on_click` | `—` | `None` | Callback called when the control is clicked. |
| `on_hover` | `—` | `None` | Callback called when the pointer's hover state changes. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
