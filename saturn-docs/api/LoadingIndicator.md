# LoadingIndicator

Shows ongoing activity with an animated shape.

[← API index](./README.md)

Source: [`saturn/widgets/expressive_progress.py`](../../saturn/widgets/expressive_progress.py) (line 32).

## Preview

![LoadingIndicator control in the dark theme](../images/controls/LoadingIndicator.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.LoadingIndicator(contained=True, width=72, height=72))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.LoadingIndicator(value=None, *, color=None, bgcolor=None, contained=False, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `value` | `—` | `None` | Current value of the control or data object. |
| `color` | `—` | `None` | Color of foreground content, text, or drawing. |
| `bgcolor` | `—` | `None` | Background color of the control or container. |
| `contained` | `—` | `False` | Place the loading indicator on a container background. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
