# Text

Displays text with configurable size, weight, and color.

[← API index](./README.md)

Source: [`saturn/widgets/text.py`](../../saturn/widgets/text.py) (line 13).

## Preview

![Text control in the dark theme](../../.static/controls/Text.png)

## Example

Run this code from the repository root to display the control shown above.

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Text("Hello, Saturn", size=30, weight=saturn.FontWeight.BOLD))
    page.update()


saturn.run(main, backend=saturn.Renderer.SOFTWARE, width=720, height=360)
```

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.Text(value: 'str' = '', *, size: 'float | None' = None, color=None, weight=None, italic: 'bool' = False, text_align=None, max_lines: 'int | None' = None, no_wrap: 'bool' = False, selectable: 'bool | None' = None, font_family: 'str | None' = None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `value` | `str` | `''` | Text content to display. |
| `size` | `float | None` | `None` | Size of the text, icon, or control. |
| `color` | `—` | `None` | Color of foreground content, text, or drawing. |
| `weight` | `—` | `None` | Text font weight. |
| `italic` | `bool` | `False` | Whether to use italic text. |
| `text_align` | `—` | `None` | Text alignment within the available width. |
| `max_lines` | `int | None` | `None` | Maximum number of lines to show or accept. |
| `no_wrap` | `bool` | `False` | Prevent automatic line wrapping when True. |
| `selectable` | `bool | None` | `None` | Whether text can be selected with the pointer. |
| `font_family` | `str | None` | `None` | Font family name registered on the page. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
