# ListItem

An interactive or passive M3 Expressive list row.

[← API 索引](./README.md)

源码：[`saturn/widgets/list_item.py`](../../saturn/widgets/list_item.py)（第 30 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.ListItem(content=None, *, headline=None, leading=None, trailing=None, overline=None, supporting=None, selected=False, container_color=None, selected_container_color=None, content_color=None, selected_content_color=None, border_radius=None, on_click=None, on_hover=None, on_long_press=None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `content` | `—` | `None` |
| `headline` | `—` | `None` |
| `leading` | `—` | `None` |
| `trailing` | `—` | `None` |
| `overline` | `—` | `None` |
| `supporting` | `—` | `None` |
| `selected` | `—` | `False` |
| `container_color` | `—` | `None` |
| `selected_container_color` | `—` | `None` |
| `content_color` | `—` | `None` |
| `selected_content_color` | `—` | `None` |
| `border_radius` | `—` | `None` |
| `on_click` | `—` | `None` |
| `on_hover` | `—` | `None` |
| `on_long_press` | `—` | `None` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`border_radius`、`container_color`、`content_color`、`headline`、`leading`、`overline`、`selected`、`selected_container_color`、`selected_content_color`、`supporting`、`trailing`。

## 事件回调

`on_click`、`on_hover`、`on_long_press`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
