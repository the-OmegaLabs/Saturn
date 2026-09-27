# Radio

Single choice in a mutually exclusive group.

[← API index](./README.md)

Source: [`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py) (line 1171).

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
saturn.Radio(value=None, *, label: 'str' = '', label_position=<LabelPosition.RIGHT: 'right'>, active_color=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `value` | `—` | `None` | Current value of the control or data object. |
| `label` | `str` | `''` | Label beside an input, option, or control. |
| `label_position` | `—` | `<LabelPosition.RIGHT: 'right'>` | Position of the label relative to the selection control. |
| `active_color` | `—` | `None` | Color used in the selected or on state. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
