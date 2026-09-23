# ProgressBar

Saturn 的 ProgressBar 公开 API。

[← API 索引](./README.md)

源码：[`saturn/widgets/basic.py`](../../saturn/widgets/basic.py)（第 164 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.ProgressBar(value: 'float | None' = None, *, bar_height: 'float' = 4, color=None, bgcolor=None, border_radius=None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `value` | `float | None` | `None` |
| `bar_height` | `float` | `4` |
| `color` | `—` | `None` |
| `bgcolor` | `—` | `None` |
| `border_radius` | `—` | `None` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`bar_height`、`bgcolor`、`border_radius`、`color`、`value`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
