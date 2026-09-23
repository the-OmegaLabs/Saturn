# Card

带有表面和阴影的内容容器。

[← API 索引](./README.md)

源码：[`saturn/widgets/basic.py`](../../saturn/widgets/basic.py)（第 140 行）。

## 效果图

![Card 控件的深色主题效果](../images/controls/Card.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Card(saturn.Container(saturn.Text("Card content"), padding=24), elevation=3))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Container](./Container.md)

## 构造参数

```python
saturn.Card(content=None, *, elevation: 'float' = 1, variant: 'str' = 'elevated', **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `content` | `—` | `None` | 要显示的文本或子控件。 |
| `elevation` | `float` | `1` | 表面高度，对应阴影的视觉强度。 |
| `variant` | `str` | `'elevated'` | 选择该控件的视觉变体。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
