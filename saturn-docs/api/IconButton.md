# IconButton

Saturn 的 IconButton 公开 API。

[← API 索引](./README.md)

源码：[`saturn/widgets/buttons.py`](../../saturn/widgets/buttons.py)（第 300 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.IconButton(icon, *, icon_size: 'float | None' = None, icon_color=None, selected_icon=None, selected=False, bgcolor=None, hover_color=None, tooltip=None, on_click=None, on_hover=None, expressive=False, size=None, shape='round', **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `icon` | `—` | `必填` |
| `icon_size` | `float | None` | `None` |
| `icon_color` | `—` | `None` |
| `selected_icon` | `—` | `None` |
| `selected` | `—` | `False` |
| `bgcolor` | `—` | `None` |
| `hover_color` | `—` | `None` |
| `tooltip` | `—` | `None` |
| `on_click` | `—` | `None` |
| `on_hover` | `—` | `None` |
| `expressive` | `—` | `False` |
| `size` | `—` | `None` |
| `shape` | `—` | `'round'` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`bgcolor`、`button_shape`、`button_size`、`expressive`、`hover_color`、`icon`、`icon_color`、`icon_size`、`selected`、`selected_icon`。

## 事件回调

`on_click`、`on_hover`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
