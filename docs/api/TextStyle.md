# TextStyle

Combines text size, weight, color, spacing, and other styles.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 352).

## Constructor parameters

```python
saturn.TextStyle(size: 'float | None' = None, weight: 'FontWeight | None' = None, italic: 'bool' = False, color: 'object' = None, bgcolor: 'object' = None, font_family: 'str | None' = None, letter_spacing: 'float | None' = None, overflow: 'TextOverflow | None' = None) -> None
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
