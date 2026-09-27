# Switch

Sliding on/off toggle.

[← API index](./README.md)

Source: [`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py) (line 1476).

## Preview

![Switch control in the dark theme](../../.static/controls/Switch.png)

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
    page.add(saturn.Switch("Notifications", value=True))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE)
```

**Base class:** `_Toggle`

## Constructor parameters

```python
saturn.Switch(label='', *, value=False, label_position=<LabelPosition.RIGHT: 'right'>, label_text_style=None, autofocus=False, active_color=None, active_track_color=None, inactive_thumb_color=None, inactive_track_color=None, thumb_color=None, thumb_icon=None, track_color=None, track_outline_color=None, track_outline_width=None, overlay_color=None, focus_color=None, hover_color=None, splash_radius=None, padding=None, on_change=None, on_focus=None, on_blur=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `label` | `—` | `''` | Label beside an input, option, or control. |
| `value` | `—` | `False` | Current value of the control or data object. |
| `label_position` | `—` | `<LabelPosition.RIGHT: 'right'>` | Position of the label relative to the selection control. |
| `label_text_style` | `—` | `None` | Style applied to label text. |
| `autofocus` | `—` | `False` | Try to focus this control when the page opens. |
| `active_color` | `—` | `None` | Color used in the selected or on state. |
| `active_track_color` | `—` | `None` | Color for active track. |
| `inactive_thumb_color` | `—` | `None` | Color for inactive thumb. |
| `inactive_track_color` | `—` | `None` | Color for inactive track. |
| `thumb_color` | `—` | `None` | Color of the slider thumb. |
| `thumb_icon` | `—` | `None` | Icon used for thumb. |
| `track_color` | `—` | `None` | Color for track. |
| `track_outline_color` | `—` | `None` | Color for track outline. |
| `track_outline_width` | `—` | `None` | Switch track outline thickness. |
| `overlay_color` | `—` | `None` | Color for overlay. |
| `focus_color` | `—` | `None` | Color for focus. |
| `hover_color` | `—` | `None` | Color used in the hover state. |
| `splash_radius` | `—` | `None` | Pointer feedback radius limit. |
| `padding` | `—` | `None` | Space around the control's content. |
| `on_change` | `—` | `None` | Callback called when the value changes. |
| `on_focus` | `—` | `None` | Callback called when the control gains focus. |
| `on_blur` | `—` | `None` | Callback called when the control loses focus. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
