# TextField

可编辑的文本输入框。

[← API 索引](./README.md)

源码：[`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py)（第 76 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.TextField(value: 'str' = '', *, label=None, hint_text=None, password: 'bool' = False, multiline: 'bool' = False, max_lines: 'int | None' = None, read_only: 'bool' = False, text_size: 'float | None' = None, on_change=None, on_submit=None, on_focus=None, on_blur=None, on_click=None, filled: 'bool' = False, bgcolor=None, border_color=None, cursor_color=None, border_radius: 'float | None' = None, border=None, text_style=None, can_reveal_password: 'bool' = False, on_hover=None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `value` | `str` | `''` |
| `label` | `—` | `None` |
| `hint_text` | `—` | `None` |
| `password` | `bool` | `False` |
| `multiline` | `bool` | `False` |
| `max_lines` | `int | None` | `None` |
| `read_only` | `bool` | `False` |
| `text_size` | `float | None` | `None` |
| `on_change` | `—` | `None` |
| `on_submit` | `—` | `None` |
| `on_focus` | `—` | `None` |
| `on_blur` | `—` | `None` |
| `on_click` | `—` | `None` |
| `filled` | `bool` | `False` |
| `bgcolor` | `—` | `None` |
| `border_color` | `—` | `None` |
| `cursor_color` | `—` | `None` |
| `border_radius` | `float | None` | `None` |
| `border` | `—` | `None` |
| `text_style` | `—` | `None` |
| `can_reveal_password` | `bool` | `False` |
| `on_hover` | `—` | `None` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`bgcolor`、`border`、`border_color`、`border_radius`、`can_reveal_password`、`cursor_color`、`filled`、`hint_text`、`label`、`max_lines`、`multiline`、`password`、`read_only`、`text_size`、`text_style`、`value`。

## 事件回调

`on_blur`、`on_change`、`on_click`、`on_focus`、`on_hover`、`on_submit`。

## 效果预览

![输入与反馈 展示](../../shots/inputs-demo.png)

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
