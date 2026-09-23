# GestureDetector

Receives pointer and gesture events.

[← API index](./README.md)

Source: [`saturn/widgets/scrolling.py`](../../saturn/widgets/scrolling.py) (line 350).

## Preview

![GestureDetector control in the dark theme](../images/controls/GestureDetector.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.GestureDetector(saturn.Container(saturn.Text("Tap this surface"), padding=20, bgcolor=saturn.Colors.PRIMARY_CONTAINER, border_radius=12), on_tap=lambda event: None))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.GestureDetector(content=None, *, on_tap=None, on_tap_down=None, on_long_press=None, on_hover=None, on_enter=None, on_exit=None, mouse_cursor=None, drag_interval=0, hover_interval=0, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `content` | `—` | `None` | Text or child control to display. |
| `on_tap` | `—` | `None` | Callback called when a tap completes. |
| `on_tap_down` | `—` | `None` | Callback called when a press begins. |
| `on_long_press` | `—` | `None` | Callback called when the control is long pressed. |
| `on_hover` | `—` | `None` | Callback called when the pointer's hover state changes. |
| `on_enter` | `—` | `None` | Callback called when the pointer enters the control. |
| `on_exit` | `—` | `None` | Callback called when the pointer leaves the control. |
| `mouse_cursor` | `—` | `None` | Pointer style shown on hover. |
| `drag_interval` | `—` | `0` | Minimum interval between consecutive drag events. |
| `hover_interval` | `—` | `0` | Minimum interval between consecutive hover events. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
