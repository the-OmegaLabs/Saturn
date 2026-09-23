# SnackBar

显示短暂的操作反馈。

[← API 索引](./README.md)

源码：[`saturn/widgets/dialogs.py`](../../saturn/widgets/dialogs.py)（第 227 行）。

**基类：** `DialogControl`

## 构造

```python
ft.SnackBar(content, *, action=None, bgcolor=None, duration: 'int' = 4000, on_action=None, open=False, on_dismiss=None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `content` | `—` | `必填` |
| `action` | `—` | `None` |
| `bgcolor` | `—` | `None` |
| `duration` | `int` | `4000` |
| `on_action` | `—` | `None` |
| `open` | `—` | `False` |
| `on_dismiss` | `—` | `None` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`action`、`bgcolor`、`content`、`duration`。

## 事件回调

`on_action`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
