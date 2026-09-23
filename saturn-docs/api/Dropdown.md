# Dropdown

从选项列表中选择一个值。

[← API 索引](./README.md)

源码：[`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py)（第 1468 行）。

## 效果图

![Dropdown 控件的深色主题效果](../images/controls/Dropdown.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Dropdown(hint_text="Choose a format", options=[saturn.Option("pdf", text="PDF"), saturn.Option("csv", text="CSV")], width=300))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.Dropdown(value=None, *, options=None, hint_text=None, label=None, on_select=None, text_size: 'float' = 16.0, filled=False, fill_color=None, bgcolor=None, border=None, border_radius=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `value` | `—` | `None` | 当前选中选项的键。 |
| `options` | `—` | `None` | 下拉菜单中的可选项。 |
| `hint_text` | `—` | `None` | 尚无输入或选择时显示的提示文字。 |
| `label` | `—` | `None` | 显示在输入框、选项或控件旁的标签。 |
| `on_select` | `—` | `None` | 选中菜单项或选项时调用的回调。 |
| `text_size` | `float` | `16.0` | 输入或选择内容的文字大小。 |
| `filled` | `—` | `False` | 是否使用填充式输入区域。 |
| `fill_color` | `—` | `None` | 填充式输入区域的背景颜色。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `border` | `—` | `None` | 边框配置。 |
| `border_radius` | `—` | `None` | 边框或背景的圆角半径。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
