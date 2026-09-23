# Dropdown

从选项列表中选择一个值。

[← API 索引](./README.md)

源码：[`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py)（第 1468 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.Dropdown(value=None, *, options=None, hint_text=None, label=None, on_select=None, text_size: 'float' = 16.0, filled=False, fill_color=None, bgcolor=None, border=None, border_radius=None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `value` | `—` | `None` |
| `options` | `—` | `None` |
| `hint_text` | `—` | `None` |
| `label` | `—` | `None` |
| `on_select` | `—` | `None` |
| `text_size` | `float` | `16.0` |
| `filled` | `—` | `False` |
| `fill_color` | `—` | `None` |
| `bgcolor` | `—` | `None` |
| `border` | `—` | `None` |
| `border_radius` | `—` | `None` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`bgcolor`、`border`、`border_radius`、`fill_color`、`filled`、`hint_text`、`label`、`open`、`options`、`text_size`、`value`。

## 事件回调

`on_click`、`on_select`。

## 效果预览

![输入与反馈 展示](../../shots/inputs-demo.png)

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
