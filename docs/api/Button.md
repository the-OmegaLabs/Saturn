# Button

Basic clickable button.

[← API index](./README.md)

Source: [`saturn/widgets/buttons.py`](../../saturn/widgets/buttons.py) (line 291).

## Preview

![Button control in the dark theme](../../.static/controls/Button.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Button("Open project", icon=saturn.Icons.FOLDER_OPEN))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE, width=720, height=360)
```

The public name `saturn.Button` refers to the implementation class `_ConcreteButton`.

## Constructor parameters

```python
saturn.Button(content=None, *, icon=None, icon_color=None, color=None, bgcolor=None, elevation: 'float' = 1, style=None, on_click=None, on_hover=None, on_long_press=None, on_focus=None, on_blur=None, autofocus=False, url=None, expressive=False, size=None, shape='round', **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `content` | `—` | `None` | Text or control displayed on the button. |
| `icon` | `—` | `None` | Icon to draw. |
| `icon_color` | `—` | `None` | Foreground color of the icon. |
| `color` | `—` | `None` | Color of foreground content, text, or drawing. |
| `bgcolor` | `—` | `None` | Background color of the control or container. |
| `elevation` | `float` | `1` | Surface elevation, which determines shadow strength. |
| `style` | `—` | `None` | Additional button style settings. |
| `on_click` | `—` | `None` | Callback called when the control is clicked. |
| `on_hover` | `—` | `None` | Callback called when the pointer's hover state changes. |
| `on_long_press` | `—` | `None` | Callback called when the control is long pressed. |
| `on_focus` | `—` | `None` | Callback called when the control gains focus. |
| `on_blur` | `—` | `None` | Callback called when the control loses focus. |
| `autofocus` | `—` | `False` | Try to focus this control when the page opens. |
| `url` | `—` | `None` | Destination opened when the button is clicked. |
| `expressive` | `—` | `False` | Enable Expressive sizing and shape behavior. |
| `size` | `—` | `None` | Size of the text, icon, or control. |
| `shape` | `—` | `'round'` | Base shape of the button. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
