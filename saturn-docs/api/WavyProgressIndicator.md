# WavyProgressIndicator

以波浪线条展示进度。

[← API 索引](./README.md)

源码：[`saturn/widgets/expressive_progress.py`](../../saturn/widgets/expressive_progress.py)（第 106 行）。

## 效果图

![WavyProgressIndicator 控件的深色主题效果](../images/controls/WavyProgressIndicator.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.WavyProgressIndicator(0.65, width=320))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.WavyProgressIndicator(value=None, *, color=None, bgcolor=None, stroke_width=4, amplitude=None, wavelength=None, wave_speed=1.0, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `value` | `—` | `None` | 控件或数据对象的当前值。 |
| `color` | `—` | `None` | 前景、文字或绘制内容的颜色。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `stroke_width` | `—` | `4` | 进度环或波形线条的宽度。 |
| `amplitude` | `—` | `None` | 波浪相对基线的起伏高度。 |
| `wavelength` | `—` | `None` | 波形相邻峰值之间的距离。 |
| `wave_speed` | `—` | `1.0` | 波形动画的移动速度。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
