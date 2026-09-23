# FloatingActionButtonMenu

An anchored FAB with scrollable actions. Outside click or Escape closes it.

[← API 索引](./README.md)

源码：[`saturn/widgets/floating.py`](../../saturn/widgets/floating.py)（第 248 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.FloatingActionButtonMenu(items=None, *, icon=<Icons.ADD: 57669>, expanded=False, on_select=None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `items` | `—` | `None` |
| `icon` | `—` | `<Icons.ADD: 57669>` |
| `expanded` | `—` | `False` |
| `on_select` | `—` | `None` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`fab`、`items`。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `toggle(self)` | — |
| `close(self)` | — |

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
