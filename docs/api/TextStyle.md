# TextStyle

Combines text size, weight, color, spacing, and other styles.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 482).

## Constructor parameters

```python
saturn.TextStyle(size: 'float | None' = None, weight: 'FontWeight | None' = None, italic: 'bool' = False, color: 'object' = None, bgcolor: 'object' = None, font_family: 'str | None' = None, letter_spacing: 'float | None' = None, overflow: 'TextOverflow | None' = None, height: 'float | None' = None, word_spacing: 'float | None' = None, decoration: 'object' = None, decoration_color: 'object' = None, decoration_thickness: 'float | None' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `size` | `float | None` | `None` | Size of the text, icon, or control. |
| `weight` | `FontWeight | None` | `None` | Text font weight. |
| `italic` | `bool` | `False` | Whether to use italic text. |
| `color` | `object` | `None` | Color of foreground content, text, or drawing. |
| `bgcolor` | `object` | `None` | Background color of the control or container. |
| `font_family` | `str | None` | `None` | Font family name registered on the page. |
| `letter_spacing` | `float | None` | `None` | Extra space between characters. |
| `overflow` | `TextOverflow | None` | `None` | How to handle text beyond the available space. |
| `height` | `float | None` | `None` | Specified control height. |
| `word_spacing` | `float | None` | `None` | Extra spacing between words; nonzero requests are unsupported. |
| `decoration` | `object` | `None` | Text or border decoration settings. |
| `decoration_color` | `object` | `None` | Color for decoration. |
| `decoration_thickness` | `float | None` | `None` | Text decoration thickness; non-default requests are unsupported. |
