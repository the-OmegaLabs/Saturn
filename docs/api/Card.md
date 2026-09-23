# Card

Content container with a surface and shadow.

[← API index](./README.md)

Source: [`saturn/widgets/basic.py`](../../saturn/widgets/basic.py) (line 146).

## Preview

![Card control in the dark theme](../../.static/controls/Card.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Card(saturn.Container(saturn.Text("Card content"), padding=24), elevation=3))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE, width=720, height=360)
```

**Base class:** [Container](./Container.md)

## Constructor parameters

```python
saturn.Card(content=None, *, elevation: 'float' = 1, variant: 'str' = 'elevated', **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `content` | `—` | `None` | Text or child control to display. |
| `elevation` | `float` | `1` | Surface elevation, which determines shadow strength. |
| `variant` | `str` | `'elevated'` | Visual variant of this control. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
