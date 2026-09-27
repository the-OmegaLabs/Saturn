# ProgressRing

Shows determinate or indeterminate progress as a ring.

[← API index](./README.md)

Source: [`saturn/widgets/basic.py`](../../saturn/widgets/basic.py) (line 480).

## Preview

![ProgressRing control in the dark theme](../../.static/controls/ProgressRing.png)

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
    page.add(saturn.ProgressRing(0.65))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.ProgressRing(value: 'float | None' = None, *, stroke_width: 'float' = 4, color=None, bgcolor=None, stroke_align=None, stroke_cap=None, semantics_label=None, semantics_value=None, track_gap=None, size_constraints=None, padding=None, year_2023=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `value` | `float | None` | `None` | Progress, usually from 0 to 1; None means indeterminate. |
| `stroke_width` | `float` | `4` | Width of a progress ring or wave stroke. |
| `color` | `—` | `None` | Color of foreground content, text, or drawing. |
| `bgcolor` | `—` | `None` | Background color of the control or container. |
| `stroke_align` | `—` | `None` | Alignment of the progress stroke relative to its bounds. |
| `stroke_cap` | `—` | `None` | Shape of stroke endpoints. |
| `semantics_label` | `—` | `None` | Accessibility description metadata; native accessibility is not implemented. |
| `semantics_value` | `—` | `None` | Accessibility value metadata. |
| `track_gap` | `—` | `None` | Gap between a progress stroke and its track. |
| `size_constraints` | `—` | `None` | Allowed minimum and maximum dimensions. |
| `padding` | `—` | `None` | Space around the control's content. |
| `year_2023` | `—` | `None` | Requested year 2023 option; see the control comparison for supported values and restrictions. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
