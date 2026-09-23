# TextField

可编辑的文本输入框。

[← API 索引](./README.md)

源码：[`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py)（第 76 行）。

## 效果图

![TextField 控件的深色主题效果](../images/controls/TextField.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.TextField("Saturn", label="Project name", width=340))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.TextField(value: 'str' = '', *, label=None, hint_text=None, password: 'bool' = False, multiline: 'bool' = False, max_lines: 'int | None' = None, read_only: 'bool' = False, text_size: 'float | None' = None, on_change=None, on_submit=None, on_focus=None, on_blur=None, on_click=None, filled: 'bool' = False, bgcolor=None, border_color=None, cursor_color=None, border_radius: 'float | None' = None, border=None, text_style=None, can_reveal_password: 'bool' = False, on_hover=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `value` | `str` | `''` | 文本框初始或当前输入内容。 |
| `label` | `—` | `None` | 显示在输入框、选项或控件旁的标签。 |
| `hint_text` | `—` | `None` | 尚无输入或选择时显示的提示文字。 |
| `password` | `bool` | `False` | 为 True 时遮蔽输入字符。 |
| `multiline` | `bool` | `False` | 是否允许输入多行文本。 |
| `max_lines` | `int | None` | `None` | 最多显示或输入的行数。 |
| `read_only` | `bool` | `False` | 为 True 时显示内容但不允许编辑。 |
| `text_size` | `float | None` | `None` | 输入或选择内容的文字大小。 |
| `on_change` | `—` | `None` | 值改变时调用的回调。 |
| `on_submit` | `—` | `None` | 提交输入内容时调用的回调。 |
| `on_focus` | `—` | `None` | 控件获得焦点时调用的回调。 |
| `on_blur` | `—` | `None` | 控件失去焦点时调用的回调。 |
| `on_click` | `—` | `None` | 点击控件时调用的回调。 |
| `filled` | `bool` | `False` | 是否使用填充式输入区域。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `border_color` | `—` | `None` | 输入区域的边框颜色。 |
| `cursor_color` | `—` | `None` | 文本插入光标的颜色。 |
| `border_radius` | `float | None` | `None` | 边框或背景的圆角半径。 |
| `border` | `—` | `None` | 边框配置。 |
| `text_style` | `—` | `None` | 输入或显示文字的样式。 |
| `can_reveal_password` | `bool` | `False` | 是否提供显示密码的切换按钮。 |
| `on_hover` | `—` | `None` | 指针悬停状态变化时调用的回调。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
