# SplitButton

Two independently clickable segments; ``on_click`` is the main action.

[← API 索引](./README.md)

源码：[`saturn/widgets/split_button.py`](../../saturn/widgets/split_button.py)（第 106 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.SplitButton(content: 'str' = '', *, icon=None, trailing_icon=<Icons.ARROW_DROP_DOWN: 58821>, on_click=None, on_trailing_click=None, bgcolor=None, color=None, **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `content` | `str` | `''` |
| `icon` | `—` | `None` |
| `trailing_icon` | `—` | `<Icons.ARROW_DROP_DOWN: 58821>` |
| `on_click` | `—` | `None` |
| `on_trailing_click` | `—` | `None` |
| `bgcolor` | `—` | `None` |
| `color` | `—` | `None` |
| `base` | `—` | `额外关键字参数` |

## 本类属性

`content`、`icon`、`leading_button`、`trailing_button`、`trailing_icon`。

## 事件回调

`on_click`、`on_trailing_click`。

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
