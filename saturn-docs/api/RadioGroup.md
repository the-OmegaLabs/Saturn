# RadioGroup

Manages the selected value among Radio controls.

[← API index](./README.md)

Source: [`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py) (line 1069).

## Preview

![RadioGroup control in the dark theme](../images/controls/RadioGroup.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.RadioGroup(saturn.Row([saturn.Radio("day", label="Day"), saturn.Radio("week", label="Week")]), value="day"))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.RadioGroup(content=None, *, value=None, on_change=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `content` | `—` | `None` | Text or child control to display. |
| `value` | `—` | `None` | Current value of the control or data object. |
| `on_change` | `—` | `None` | Callback called when the value changes. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
