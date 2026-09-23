# GestureDetector

接收指针和手势事件。

[← API 索引](./README.md)

源码：[`saturn/widgets/scrolling.py`](../../saturn/widgets/scrolling.py)（第 337 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.GestureDetector(content=None, *, on_tap=None, on_tap_down=None, on_long_press=None, on_hover=None, on_enter=None, on_exit=None, mouse_cursor=None, drag_interval=0, hover_interval=0, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `content` | `—` | `None` |
| `on_tap` | `—` | `None` |
| `on_tap_down` | `—` | `None` |
| `on_long_press` | `—` | `None` |
| `on_hover` | `—` | `None` |
| `on_enter` | `—` | `None` |
| `on_exit` | `—` | `None` |
| `mouse_cursor` | `—` | `None` |
| `drag_interval` | `—` | `0` |
| `hover_interval` | `—` | `0` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`content`、`mouse_cursor`。

## 事件回调

`on_click`、`on_enter`、`on_exit`、`on_hover`、`on_long_press`、`on_tap`、`on_tap_down`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
