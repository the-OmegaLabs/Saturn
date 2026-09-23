# Text

显示文本并设置字号、字重和颜色。

[← API 索引](./README.md)

源码：[`saturn/widgets/text.py`](../../saturn/widgets/text.py)（第 12 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.Text(value: 'str' = '', *, size: 'float | None' = None, color=None, weight=None, italic: 'bool' = False, text_align=None, max_lines: 'int | None' = None, no_wrap: 'bool' = False, selectable: 'bool | None' = None, font_family: 'str | None' = None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `value` | `str` | `''` |
| `size` | `float | None` | `None` |
| `color` | `—` | `None` |
| `weight` | `—` | `None` |
| `italic` | `bool` | `False` |
| `text_align` | `—` | `None` |
| `max_lines` | `int | None` | `None` |
| `no_wrap` | `bool` | `False` |
| `selectable` | `bool | None` | `None` |
| `font_family` | `str | None` | `None` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`color`、`font_family`、`italic`、`max_lines`、`no_wrap`、`selectable`、`size`、`text_align`、`value`、`weight`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
