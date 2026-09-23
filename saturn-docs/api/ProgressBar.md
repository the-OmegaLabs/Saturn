# ProgressBar

以水平线条显示已知或不确定进度。

[← API 索引](./README.md)

源码：[`saturn/widgets/basic.py`](../../saturn/widgets/basic.py)（第 164 行）。

## 效果图

![ProgressBar 控件的深色主题效果](../images/controls/ProgressBar.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ProgressBar(0.65, width=320))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.ProgressBar(value: 'float | None' = None, *, bar_height: 'float' = 4, color=None, bgcolor=None, border_radius=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `value` | `float | None` | `None` | 进度值，通常在 0 到 1 之间；None 表示不确定进度。 |
| `bar_height` | `float` | `4` | 线性进度条的厚度。 |
| `color` | `—` | `None` | 前景、文字或绘制内容的颜色。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `border_radius` | `—` | `None` | 边框或背景的圆角半径。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
