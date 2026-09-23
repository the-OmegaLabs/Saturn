# Image

显示本地图片或 SVG。

[← API 索引](./README.md)

源码：[`saturn/widgets/basic.py`](../../saturn/widgets/basic.py)（第 71 行）。

## 效果图

![Image 控件的深色主题效果](../images/controls/Image.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Image("examples/assets/test_img.png", width=300, height=150, border_radius=12))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.Image(src=None, *, fit=None, border_radius=None, color=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `src` | `—` | `None` | 图片来源，可为本地路径、字节数据或 data URI。 |
| `fit` | `—` | `None` | 图片在给定尺寸内的缩放和裁切方式。 |
| `border_radius` | `—` | `None` | 边框或背景的圆角半径。 |
| `color` | `—` | `None` | 可选的图片着色颜色，会与原像素相乘。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
