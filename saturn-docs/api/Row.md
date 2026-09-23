# Row

横向排列子控件。

[← API 索引](./README.md)

源码：[`saturn/widgets/containers.py`](../../saturn/widgets/containers.py)（第 168 行）。

## 效果图

![Row 控件的深色主题效果](../images/controls/Row.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Row([saturn.Icon(saturn.Icons.STAR), saturn.Text("In one row"), saturn.FilledButton("Open")], spacing=16))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** `_Multi`

## 构造参数

```python
saturn.Row(*items, controls=None, alignment=<MainAxisAlignment.START: 'start'>, vertical_alignment=None, horizontal_alignment=None, spacing: 'float' = 10, tight: 'bool' = False, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `*items` | `—` | `额外位置参数` | 传给布局、分组或菜单的项目列表。 |
| `controls` | `—` | `None` | 按顺序排列的子控件列表。 |
| `alignment` | `—` | `<MainAxisAlignment.START: 'start'>` | 子控件沿水平主轴的排列方式。 |
| `vertical_alignment` | `—` | `None` | 纵向或交叉轴上的对齐方式。 |
| `horizontal_alignment` | `—` | `None` | 横向或交叉轴上的对齐方式。 |
| `spacing` | `float` | `10` | 相邻子控件之间的间距。 |
| `tight` | `bool` | `False` | 使布局尽量贴合子控件的实际尺寸。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
