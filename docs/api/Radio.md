# Radio

Single choice in a mutually exclusive group.

[← API index](./README.md)

Source: [`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py) (line 1669).

## Preview

![Radio control in the dark theme](../../.static/controls/Radio.png)

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
    page.add(saturn.Radio("standard", label="Standard"))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.Radio(value=None, *, label: 'str' = '', label_position=<LabelPosition.RIGHT: 'right'>, label_style=None, autofocus=False, active_color=None, fill_color=None, overlay_color=None, hover_color=None, focus_color=None, splash_radius=None, toggleable=False, visual_density=None, on_focus=None, on_blur=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `value` | `—` | `None` | Current value of the control or data object. |
| `label` | `str` | `''` | Label beside an input, option, or control. |
| `label_position` | `—` | `<LabelPosition.RIGHT: 'right'>` | Position of the label relative to the selection control. |
| `label_style` | `—` | `None` | Style applied to label. |
| `autofocus` | `—` | `False` | Try to focus this control when the page opens. |
| `active_color` | `—` | `None` | Color used in the selected or on state. |
| `fill_color` | `—` | `None` | Background color of a filled input area. |
| `overlay_color` | `—` | `None` | Color for overlay. |
| `hover_color` | `—` | `None` | Color used in the hover state. |
| `focus_color` | `—` | `None` | Color for focus. |
| `splash_radius` | `—` | `None` | Pointer feedback radius limit. |
| `toggleable` | `—` | `False` | Allow a selected Radio to become unselected. |
| `visual_density` | `—` | `None` | Unsupported for non-default requests. Compact, comfortable, or standard control sizing where supported. |
| `on_focus` | `—` | `None` | Callback called when the control gains focus. |
| `on_blur` | `—` | `None` | Callback called when the control loses focus. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
