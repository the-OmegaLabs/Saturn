# FloatingActionButton

用于突出页面主要操作的浮动按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/fab.py`](../../saturn/widgets/fab.py)（第 24 行）。

## 效果图

![FloatingActionButton 控件的深色主题效果](../images/controls/FloatingActionButton.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.FloatingActionButton(saturn.Icons.ADD))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** `_ConcreteButton`

## 构造参数

```python
saturn.FloatingActionButton(icon=None, *, text: 'str | None' = None, size: 'str' = 'standard', expanded: 'bool' = True, bgcolor=None, color=None, elevation: 'float' = 6.0, on_click=None, on_hover=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `icon` | `—` | `None` | 要绘制的图标。 |
| `text` | `str | None` | `None` | 显示在控件上的文字。 |
| `size` | `str` | `'standard'` | 文字、图标或控件的尺寸等级。 |
| `expanded` | `bool` | `True` | 浮动组件或菜单当前是否展开。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `color` | `—` | `None` | 前景、文字或绘制内容的颜色。 |
| `elevation` | `float` | `6.0` | 表面高度，对应阴影的视觉强度。 |
| `on_click` | `—` | `None` | 点击控件时调用的回调。 |
| `on_hover` | `—` | `None` | 指针悬停状态变化时调用的回调。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
