# Slider

Selects a value in a range by dragging a thumb.

[← API index](./README.md)

Source: [`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py) (line 1216).

## Preview

![Slider control in the dark theme](../../.static/controls/Slider.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Slider(value=0.65, width=320))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.Slider(value=None, *, min: 'float' = 0.0, max: 'float' = 1.0, divisions: 'int | None' = None, label=None, round: 'int' = 0, active_color=None, inactive_color=None, thumb_color=None, on_change=None, on_change_start=None, on_change_end=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `value` | `—` | `None` | Current slider value. |
| `min` | `float` | `0.0` | Lower bound of the selectable range. |
| `max` | `float` | `1.0` | Upper bound of the selectable range. |
| `divisions` | `int | None` | `None` | Number of discrete steps in the range. |
| `label` | `—` | `None` | Label beside an input, option, or control. |
| `round` | `int` | `0` | Number of decimal places in the displayed value. |
| `active_color` | `—` | `None` | Color used in the selected or on state. |
| `inactive_color` | `—` | `None` | Color used in the unselected state. |
| `thumb_color` | `—` | `None` | Color of the slider thumb. |
| `on_change` | `—` | `None` | Callback called when the value changes. |
| `on_change_start` | `—` | `None` | Callback called when dragging or value editing begins. |
| `on_change_end` | `—` | `None` | Callback called when dragging or value editing ends. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
