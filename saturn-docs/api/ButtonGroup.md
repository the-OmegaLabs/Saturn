# ButtonGroup

把多个按钮作为一个交互组排列。

[← API 索引](./README.md)

源码：[`saturn/widgets/button_group.py`](../../saturn/widgets/button_group.py)（第 9 行）。

## 效果图

![ButtonGroup 控件的深色主题效果](../images/controls/ButtonGroup.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ButtonGroup([saturn.ExpressiveButton("Day"), saturn.ExpressiveButton("Week"), saturn.ExpressiveButton("Month")]))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.ButtonGroup(*items, controls=None, connected=False, spacing=None, expanded_ratio=0.15, compression_limit=24.0, vertical_alignment=<CrossAxisAlignment.START: 'start'>, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `*items` | `—` | `额外位置参数` | 传给布局、分组或菜单的项目列表。 |
| `controls` | `—` | `None` | 按顺序排列的子控件列表。 |
| `connected` | `—` | `False` | 按钮组中的按钮是否采用连接式排列。 |
| `spacing` | `—` | `None` | 相邻子控件之间的间距。 |
| `expanded_ratio` | `—` | `0.15` | 按钮按压时可增加的宽度比例。 |
| `compression_limit` | `—` | `24.0` | 相邻按钮可压缩的最小尺寸限制。 |
| `vertical_alignment` | `—` | `<CrossAxisAlignment.START: 'start'>` | 纵向或交叉轴上的对齐方式。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
