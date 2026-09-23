# Option

DropdownOption 的简写名称，用来定义下拉选项。

[← API 索引](./README.md)

源码：[`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py)（第 1386 行）。

**基类：** [Control](./Control.md)

公开名称 `saturn.Option` 指向实现类 `DropdownOption`。

## 构造参数

```python
saturn.Option(key=None, *, text=None, content=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `key` | `—` | `None` | 用于定位控件或服务的键。 |
| `text` | `—` | `None` | 显示在控件上的文字。 |
| `content` | `—` | `None` | 要显示的文本或子控件。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
