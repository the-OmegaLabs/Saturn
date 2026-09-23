# ProgressRing

Shows determinate or indeterminate progress as a ring.

[← API index](./README.md)

Source: [`saturn/widgets/basic.py`](../../saturn/widgets/basic.py) (line 270).

## Preview

![ProgressRing control in the dark theme](../images/controls/ProgressRing.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ProgressRing(0.65))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.ProgressRing(value: 'float | None' = None, *, stroke_width: 'float' = 4, color=None, bgcolor=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `value` | `float | None` | `None` | Progress, usually from 0 to 1; None means indeterminate. |
| `stroke_width` | `float` | `4` | Width of a progress ring or wave stroke. |
| `color` | `—` | `None` | Color of foreground content, text, or drawing. |
| `bgcolor` | `—` | `None` | Background color of the control or container. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
