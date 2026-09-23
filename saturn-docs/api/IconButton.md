# IconButton

以图标呈现的紧凑操作按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/buttons.py`](../../saturn/widgets/buttons.py)（第 300 行）。

## 效果图

![IconButton 控件的深色主题效果](../images/controls/IconButton.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.IconButton(saturn.Icons.FAVORITE, icon_color=saturn.Colors.PRIMARY))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.IconButton(icon, *, icon_size: 'float | None' = None, icon_color=None, selected_icon=None, selected=False, bgcolor=None, hover_color=None, tooltip=None, on_click=None, on_hover=None, expressive=False, size=None, shape='round', **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `icon` | `—` | `必填` | 要绘制的图标。 |
| `icon_size` | `float | None` | `None` | 图标的显示大小。 |
| `icon_color` | `—` | `None` | 图标的前景颜色。 |
| `selected_icon` | `—` | `None` | 选中状态下显示的替代图标。 |
| `selected` | `—` | `False` | 列表项或图标按钮当前是否选中。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `hover_color` | `—` | `None` | 悬停状态使用的颜色。 |
| `tooltip` | `—` | `None` | 鼠标悬停时显示的简短提示。 |
| `on_click` | `—` | `None` | 点击控件时调用的回调。 |
| `on_hover` | `—` | `None` | 指针悬停状态变化时调用的回调。 |
| `expressive` | `—` | `False` | 是否启用 Expressive 尺寸与形状行为。 |
| `size` | `—` | `None` | 文字、图标或控件的尺寸等级。 |
| `shape` | `—` | `'round'` | 按钮的基础形状。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
