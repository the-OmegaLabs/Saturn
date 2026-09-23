# Text

显示文本并设置字号、字重和颜色。

[← API 索引](./README.md)

源码：[`saturn/widgets/text.py`](../../saturn/widgets/text.py)（第 12 行）。

## 效果图

![Text 控件的深色主题效果](../images/controls/Text.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Text("Hello, Saturn", size=30, weight=saturn.FontWeight.BOLD))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.Text(value: 'str' = '', *, size: 'float | None' = None, color=None, weight=None, italic: 'bool' = False, text_align=None, max_lines: 'int | None' = None, no_wrap: 'bool' = False, selectable: 'bool | None' = None, font_family: 'str | None' = None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `value` | `str` | `''` | 要显示的文本内容。 |
| `size` | `float | None` | `None` | 文字、图标或控件的尺寸等级。 |
| `color` | `—` | `None` | 前景、文字或绘制内容的颜色。 |
| `weight` | `—` | `None` | 文本字重。 |
| `italic` | `bool` | `False` | 是否使用斜体。 |
| `text_align` | `—` | `None` | 文本在可用宽度内的对齐方式。 |
| `max_lines` | `int | None` | `None` | 最多显示或输入的行数。 |
| `no_wrap` | `bool` | `False` | 为 True 时不自动换行。 |
| `selectable` | `bool | None` | `None` | 文本是否可被鼠标选中。 |
| `font_family` | `str | None` | `None` | 使用页面注册的字体名称。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
