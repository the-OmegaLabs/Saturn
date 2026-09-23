# ToggleButton

A toggle with unchecked, checked and pressed shapes.

[← API 索引](./README.md)

源码：[`saturn/widgets/toggle_button.py`](../../saturn/widgets/toggle_button.py)（第 15 行）。

**基类：** [ExpressiveButton](./ExpressiveButton.md)

## 构造

```python
ft.ToggleButton(content=None, *, checked=False, on_change=None, variant='filled', size='small', **kwargs)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `content` | `—` | `None` |
| `checked` | `—` | `False` |
| `on_change` | `—` | `None` |
| `variant` | `—` | `'filled'` |
| `size` | `—` | `'small'` |
| `kwargs` | `—` | `额外关键字参数` |

## 本类属性

`checked`、`variant`、`variant_bg`、`variant_border`、`variant_elevation`、`variant_fg`。

## 事件回调

`on_change`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
