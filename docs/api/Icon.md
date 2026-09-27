# Icon

Displays a Material icon.

[← API index](./README.md)

Source: [`saturn/widgets/basic.py`](../../saturn/widgets/basic.py) (line 53).

## Preview

![Icon control in the dark theme](../../.static/controls/Icon.png)

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
    page.add(saturn.Icon(saturn.Icons.FAVORITE, size=56, color=saturn.Colors.PRIMARY))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.Icon(icon, *, color=None, size: 'float' = 24, semantics_label=None, shadows=None, fill=None, apply_text_scaling=None, grade=None, weight=None, optical_size=None, blend_mode=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `icon` | `—` | `required` | Icon to draw. |
| `color` | `—` | `None` | Color of foreground content, text, or drawing. |
| `size` | `float` | `24` | Size of the text, icon, or control. |
| `semantics_label` | `—` | `None` | Accessibility description metadata; native accessibility is not implemented. |
| `shadows` | `—` | `None` | Requested shadows option; see the control comparison for supported values and restrictions. |
| `fill` | `—` | `None` | Unsupported for non-default requests. Requested fill option; see the control comparison for supported values and restrictions. |
| `apply_text_scaling` | `—` | `None` | Unsupported for non-default requests. Apply supported text/icon scaling. |
| `grade` | `—` | `None` | Unsupported for non-default requests. Requested grade option; see the control comparison for supported values and restrictions. |
| `weight` | `—` | `None` | Unsupported for non-default requests. Text font weight. |
| `optical_size` | `—` | `None` | Unsupported for non-default requests. Requested optical size option; see the control comparison for supported values and restrictions. |
| `blend_mode` | `—` | `None` | Unsupported for non-default requests. Requested blend mode option; see the control comparison for supported values and restrictions. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
