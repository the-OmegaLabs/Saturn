# ListItem

展示一行带标题、辅助文字和前后插槽的列表内容。

[← API 索引](./README.md)

源码：[`saturn/widgets/list_item.py`](../../saturn/widgets/list_item.py)（第 30 行）。

## 效果图

![ListItem 控件的深色主题效果](../images/controls/ListItem.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ListItem("Your library", supporting="24 saved items", leading=saturn.Icon(saturn.Icons.FOLDER), width=400))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.ListItem(content=None, *, headline=None, leading=None, trailing=None, overline=None, supporting=None, selected=False, container_color=None, selected_container_color=None, content_color=None, selected_content_color=None, border_radius=None, on_click=None, on_hover=None, on_long_press=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `content` | `—` | `None` | 列表项的主要显示内容。 |
| `headline` | `—` | `None` | 列表项中最醒目的主标题。 |
| `leading` | `—` | `None` | 放在主要内容前面的控件或区域。 |
| `trailing` | `—` | `None` | 放在主要内容后面的控件或区域。 |
| `overline` | `—` | `None` | 列表项标题上方的小字。 |
| `supporting` | `—` | `None` | 列表项标题下方的辅助说明。 |
| `selected` | `—` | `False` | 列表项或图标按钮当前是否选中。 |
| `container_color` | `—` | `None` | 列表项或容器在普通状态下的背景色。 |
| `selected_container_color` | `—` | `None` | 列表项选中时的背景色。 |
| `content_color` | `—` | `None` | 列表项内容在普通状态下的前景色。 |
| `selected_content_color` | `—` | `None` | 列表项选中时的前景色。 |
| `border_radius` | `—` | `None` | 边框或背景的圆角半径。 |
| `on_click` | `—` | `None` | 点击控件时调用的回调。 |
| `on_hover` | `—` | `None` | 指针悬停状态变化时调用的回调。 |
| `on_long_press` | `—` | `None` | 长按控件时调用的回调。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
