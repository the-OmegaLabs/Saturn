# Stack

按层叠顺序摆放子控件。

[← API 索引](./README.md)

源码：[`saturn/widgets/containers.py`](../../saturn/widgets/containers.py)（第 347 行）。

## 效果图

![Stack 控件的深色主题效果](../images/controls/Stack.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Stack([saturn.Container(width=230, height=110, bgcolor=saturn.Colors.PRIMARY_CONTAINER, border_radius=16), saturn.Text("Layered content", left=20, top=36)], width=230, height=110))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.Stack(*items, controls=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `*items` | `—` | `额外位置参数` | 传给布局、分组或菜单的项目列表。 |
| `controls` | `—` | `None` | 按顺序排列的子控件列表。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
