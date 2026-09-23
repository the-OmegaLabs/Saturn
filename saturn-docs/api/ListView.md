# ListView

可滚动的控件列表。

[← API 索引](./README.md)

源码：[`saturn/widgets/scrolling.py`](../../saturn/widgets/scrolling.py)（第 27 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.ListView(*items, controls=None, horizontal: 'bool' = False, spacing: 'float' = 0, padding=None, auto_scroll: 'bool' = False, on_scroll=None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `items` | `—` | `额外位置参数` |
| `controls` | `—` | `None` |
| `horizontal` | `bool` | `False` |
| `spacing` | `float` | `0` |
| `padding` | `—` | `None` |
| `auto_scroll` | `bool` | `False` |
| `on_scroll` | `—` | `None` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`auto_scroll`、`controls`、`horizontal`、`padding`、`spacing`。

## 事件回调

`on_scroll`。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `scroll_to(self, offset: 'float' = 0, delta: 'float | None' = None)` | — |

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
