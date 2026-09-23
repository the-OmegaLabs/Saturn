# Checkbox

Saturn 的 Checkbox 公开 API。

[← API 索引](./README.md)

源码：[`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py)（第 931 行）。

**基类：** `_Toggle`

## 构造

```python
ft.Checkbox(label: 'str' = '', *, value=False, active_color=None, label_position=<LabelPosition.RIGHT: 'right'>, on_change=None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `label` | `str` | `''` |
| `value` | `—` | `False` |
| `active_color` | `—` | `None` |
| `label_position` | `—` | `<LabelPosition.RIGHT: 'right'>` |
| `on_change` | `—` | `None` |
| `base` | `—` | `额外关键字参数` |

## 效果预览

![输入与反馈 展示](../../shots/inputs-demo.png)

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
