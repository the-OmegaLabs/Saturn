# Button

可响应点击的基础按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/buttons.py`](../../saturn/widgets/buttons.py)（第 291 行）。

**基类：** `Button`

公开名称 `ft.Button` 指向实现类 `_ConcreteButton`。

## 构造

```python
ft.Button(content=None, *, icon=None, icon_color=None, color=None, bgcolor=None, elevation: 'float' = 1, style=None, on_click=None, on_hover=None, on_long_press=None, on_focus=None, on_blur=None, autofocus=False, url=None, expressive=False, size=None, shape='round', **base)
```

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `content` | `—` | `None` |
| `icon` | `—` | `None` |
| `icon_color` | `—` | `None` |
| `color` | `—` | `None` |
| `bgcolor` | `—` | `None` |
| `elevation` | `float` | `1` |
| `style` | `—` | `None` |
| `on_click` | `—` | `None` |
| `on_hover` | `—` | `None` |
| `on_long_press` | `—` | `None` |
| `on_focus` | `—` | `None` |
| `on_blur` | `—` | `None` |
| `autofocus` | `—` | `False` |
| `url` | `—` | `None` |
| `expressive` | `—` | `False` |
| `size` | `—` | `None` |
| `shape` | `—` | `'round'` |
| `base` | `—` | `额外关键字参数` |

## 效果预览

![按钮与操作 展示](../../shots/buttons-demo.png)

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
