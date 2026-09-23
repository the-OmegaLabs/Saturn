# Container

为子控件添加间距、背景、边框等装饰。

[← API 索引](./README.md)

源码：[`saturn/widgets/containers.py`](../../saturn/widgets/containers.py)（第 194 行）。

## 效果图

![Container 控件的深色主题效果](../images/controls/Container.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Container(saturn.Text("A decorated container"), padding=24, bgcolor=saturn.Colors.PRIMARY_CONTAINER, border_radius=16))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.Container(content=None, *, padding=None, bgcolor=None, border=None, border_radius=None, alignment=None, gradient=None, shadow=None, ink=False, animate=None, on_click=None, on_hover=None, on_long_press=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `content` | `—` | `None` | 要显示的文本或子控件。 |
| `padding` | `—` | `None` | 控件内容四周的内边距。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `border` | `—` | `None` | 边框配置。 |
| `border_radius` | `—` | `None` | 边框或背景的圆角半径。 |
| `alignment` | `—` | `None` | 内容在容器内部的对齐位置。 |
| `gradient` | `—` | `None` | 用于填充背景的渐变。 |
| `shadow` | `—` | `None` | 控件外侧的阴影设置。 |
| `ink` | `—` | `False` | 是否绘制点击反馈的水波纹。 |
| `animate` | `—` | `None` | 属性变化时采用的动画配置。 |
| `on_click` | `—` | `None` | 点击控件时调用的回调。 |
| `on_hover` | `—` | `None` | 指针悬停状态变化时调用的回调。 |
| `on_long_press` | `—` | `None` | 长按控件时调用的回调。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
