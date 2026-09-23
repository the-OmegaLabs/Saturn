# ButtonGroup

A horizontal row whose pressed button grows into its neighbors.

[← API 索引](./README.md)

源码：[`saturn/widgets/button_group.py`](../../saturn/widgets/button_group.py)（第 9 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.ButtonGroup(*items, controls=None, connected=False, spacing=None, expanded_ratio=0.15, compression_limit=24.0, vertical_alignment=<CrossAxisAlignment.START: 'start'>, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `items` | `—` | `额外位置参数` |
| `controls` | `—` | `None` |
| `connected` | `—` | `False` |
| `spacing` | `—` | `None` |
| `expanded_ratio` | `—` | `0.15` |
| `compression_limit` | `—` | `24.0` |
| `vertical_alignment` | `—` | `<CrossAxisAlignment.START: 'start'>` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`compression_limit`、`connected`、`controls`、`expanded_ratio`、`spacing`、`vertical_alignment`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
