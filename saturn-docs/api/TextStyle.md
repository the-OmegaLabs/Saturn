# TextStyle

组合文字尺寸、字重、颜色和间距等样式。

[← API 索引](./README.md)

源码：[`saturn/types.py`](../../saturn/types.py)（第 352 行）。

## 构造参数

```python
saturn.TextStyle(size: 'float | None' = None, weight: 'FontWeight | None' = None, italic: 'bool' = False, color: 'object' = None, bgcolor: 'object' = None, font_family: 'str | None' = None, letter_spacing: 'float | None' = None, overflow: 'TextOverflow | None' = None) -> None
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `size` | `float | None` | `None` | 文字、图标或控件的尺寸等级。 |
| `weight` | `FontWeight | None` | `None` | 文本字重。 |
| `italic` | `bool` | `False` | 是否使用斜体。 |
| `color` | `object` | `None` | 前景、文字或绘制内容的颜色。 |
| `bgcolor` | `object` | `None` | 控件或容器的背景颜色。 |
| `font_family` | `str | None` | `None` | 使用页面注册的字体名称。 |
| `letter_spacing` | `float | None` | `None` | 字符之间额外增加的间距。 |
| `overflow` | `TextOverflow | None` | `None` | 文本超出可用区域时的处理方式。 |
