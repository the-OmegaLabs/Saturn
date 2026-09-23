# ProgressBar

Shows determinate or indeterminate progress as a horizontal bar.

[← API index](./README.md)

Source: [`saturn/widgets/basic.py`](../../saturn/widgets/basic.py) (line 164).

## Preview

![ProgressBar control in the dark theme](../images/controls/ProgressBar.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ProgressBar(0.65, width=320))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.ProgressBar(value: 'float | None' = None, *, bar_height: 'float' = 4, color=None, bgcolor=None, border_radius=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `value` | `float | None` | `None` | Progress, usually from 0 to 1; None means indeterminate. |
| `bar_height` | `float` | `4` | Thickness of the linear progress bar. |
| `color` | `—` | `None` | Color of foreground content, text, or drawing. |
| `bgcolor` | `—` | `None` | Background color of the control or container. |
| `border_radius` | `—` | `None` | Corner radius of the border or background. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
