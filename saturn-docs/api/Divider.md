# Divider

在相邻内容之间绘制一条分隔线。

[← API 索引](./README.md)

源码：[`saturn/widgets/containers.py`](../../saturn/widgets/containers.py)（第 411 行）。

## 效果图

![Divider 控件的深色主题效果](../images/controls/Divider.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Column([saturn.Text("Above"), saturn.Divider(), saturn.Text("Below")], width=360))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.Divider(*, height: 'float' = 16, thickness: 'float' = 1, color=None, leading_indent: 'float' = 0, trailing_indent: 'float' = 0, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `height` | `float` | `16` | 控件的指定高度。 |
| `thickness` | `float` | `1` | 线条或分隔线的粗细。 |
| `color` | `—` | `None` | 前景、文字或绘制内容的颜色。 |
| `leading_indent` | `float` | `0` | 分隔线起点留白。 |
| `trailing_indent` | `float` | `0` | 分隔线终点留白。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
