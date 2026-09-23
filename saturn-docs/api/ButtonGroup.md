# ButtonGroup

Arranges several buttons as one interactive group.

[← API index](./README.md)

Source: [`saturn/widgets/button_group.py`](../../saturn/widgets/button_group.py) (line 9).

## Preview

![ButtonGroup control in the dark theme](../images/controls/ButtonGroup.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ButtonGroup([saturn.ExpressiveButton("Day"), saturn.ExpressiveButton("Week"), saturn.ExpressiveButton("Month")]))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.ButtonGroup(*items, controls=None, connected=False, spacing=None, expanded_ratio=0.15, compression_limit=24.0, vertical_alignment=<CrossAxisAlignment.START: 'start'>, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `*items` | `—` | `additional positional arguments` | Items passed to a layout, group, or menu. |
| `controls` | `—` | `None` | Child controls in display order. |
| `connected` | `—` | `False` | Arrange buttons as a connected group. |
| `spacing` | `—` | `None` | Space between adjacent child controls. |
| `expanded_ratio` | `—` | `0.15` | Fraction by which a pressed button can grow in width. |
| `compression_limit` | `—` | `24.0` | Minimum size to which neighboring buttons can shrink. |
| `vertical_alignment` | `—` | `<CrossAxisAlignment.START: 'start'>` | Alignment on the vertical or cross axis. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
