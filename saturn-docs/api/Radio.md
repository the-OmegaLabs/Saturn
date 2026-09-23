# Radio

Saturn 的 Radio 公开 API。

[← API 索引](./README.md)

源码：[`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py)（第 1123 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.Radio(value=None, *, label: 'str' = '', label_position=<LabelPosition.RIGHT: 'right'>, active_color=None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `value` | `—` | `None` |
| `label` | `str` | `''` |
| `label_position` | `—` | `<LabelPosition.RIGHT: 'right'>` |
| `active_color` | `—` | `None` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`active_color`、`label`、`label_position`、`value`。

## 事件回调

`on_click`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
