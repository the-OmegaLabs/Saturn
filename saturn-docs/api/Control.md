# Control

所有可视控件的基类，提供尺寸、状态和更新方法。

[← API 索引](./README.md)

源码：[`saturn/control.py`](../../saturn/control.py)（第 24 行）。

## 构造

```python
ft.Control(*, visible: 'bool' = True, disabled: 'bool' = False, opacity: 'float' = 1.0, expand: 'bool | int | None' = None, tooltip: 'str | None' = None, data=None, width: 'float | None' = None, height: 'float | None' = None, margin=None, align: 'Alignment | None' = None, left: 'float | None' = None, top: 'float | None' = None, right: 'float | None' = None, bottom: 'float | None' = None, rotate=None, scale=None, offset=None, animate_opacity=None, animate_size=None, animate_position=None, animate_align=None, animate_margin=None, animate_rotation=None, animate_scale=None, animate_offset=None, on_animation_end=None, **_flet_ignored)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `visible` | `bool` | `True` |
| `disabled` | `bool` | `False` |
| `opacity` | `float` | `1.0` |
| `expand` | `bool | int | None` | `None` |
| `tooltip` | `str | None` | `None` |
| `data` | `—` | `None` |
| `width` | `float | None` | `None` |
| `height` | `float | None` | `None` |
| `margin` | `—` | `None` |
| `align` | `Alignment | None` | `None` |
| `left` | `float | None` | `None` |
| `top` | `float | None` | `None` |
| `right` | `float | None` | `None` |
| `bottom` | `float | None` | `None` |
| `rotate` | `—` | `None` |
| `scale` | `—` | `None` |
| `offset` | `—` | `None` |
| `animate_opacity` | `—` | `None` |
| `animate_size` | `—` | `None` |
| `animate_position` | `—` | `None` |
| `animate_align` | `—` | `None` |
| `animate_margin` | `—` | `None` |
| `animate_rotation` | `—` | `None` |
| `animate_scale` | `—` | `None` |
| `animate_offset` | `—` | `None` |
| `on_animation_end` | `—` | `None` |
| `_flet_ignored` | `—` | `额外关键字参数` |

## 本类属性

`align`、`animate_align`、`animate_margin`、`animate_offset`、`animate_opacity`、`animate_position`、`animate_rotation`、`animate_scale`、`animate_size`、`bottom`、`data`、`disabled`、`expand`、`height`、`left`、`margin`、`offset`、`opacity`、`page`、`parent`、`right`、`rotate`、`scale`、`tooltip`、`top`、`visible`、`width`。

## 事件回调

`on_animation_end`。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `update(self)` | — |
| `handle_event(self, e) -> 'bool'` | — |

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
