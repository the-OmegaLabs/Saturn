# LoadingIndicator

以动态形状展示正在进行的操作。

[← API 索引](./README.md)

源码：[`saturn/widgets/expressive_progress.py`](../../saturn/widgets/expressive_progress.py)（第 32 行）。

## 效果图

![LoadingIndicator 控件的深色主题效果](../images/controls/LoadingIndicator.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.LoadingIndicator(contained=True, width=72, height=72))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.LoadingIndicator(value=None, *, color=None, bgcolor=None, contained=False, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `value` | `—` | `None` | 控件或数据对象的当前值。 |
| `color` | `—` | `None` | 前景、文字或绘制内容的颜色。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `contained` | `—` | `False` | 加载指示器是否放在容器背景中。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
