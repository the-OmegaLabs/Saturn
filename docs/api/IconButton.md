# IconButton

Compact action button presented as an icon.

[← API index](./README.md)

Source: [`saturn/widgets/buttons.py`](../../saturn/widgets/buttons.py) (line 300).

## Preview

![IconButton control in the dark theme](../../.static/controls/IconButton.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.IconButton(saturn.Icons.FAVORITE, icon_color=saturn.Colors.PRIMARY))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.IconButton(icon, *, icon_size: 'float | None' = None, icon_color=None, selected_icon=None, selected=False, bgcolor=None, hover_color=None, tooltip=None, on_click=None, on_hover=None, expressive=False, size=None, shape='round', **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `icon` | `—` | `required` | Icon to draw. |
| `icon_size` | `float | None` | `None` | Displayed icon size. |
| `icon_color` | `—` | `None` | Foreground color of the icon. |
| `selected_icon` | `—` | `None` | Alternate icon shown when selected. |
| `selected` | `—` | `False` | Whether the list item or icon button is selected. |
| `bgcolor` | `—` | `None` | Background color of the control or container. |
| `hover_color` | `—` | `None` | Color used in the hover state. |
| `tooltip` | `—` | `None` | Short hint shown on hover. |
| `on_click` | `—` | `None` | Callback called when the control is clicked. |
| `on_hover` | `—` | `None` | Callback called when the pointer's hover state changes. |
| `expressive` | `—` | `False` | Enable Expressive sizing and shape behavior. |
| `size` | `—` | `None` | Size of the text, icon, or control. |
| `shape` | `—` | `'round'` | Base shape of the button. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
