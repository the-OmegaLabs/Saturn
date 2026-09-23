# FloatingToolbar

以胶囊形表面容纳一组操作的浮动工具栏。

[← API 索引](./README.md)

源码：[`saturn/widgets/floating.py`](../../saturn/widgets/floating.py)（第 18 行）。

## 效果图

![FloatingToolbar 控件的深色主题效果](../images/controls/FloatingToolbar.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.FloatingToolbar(saturn.IconButton(saturn.Icons.EDIT), saturn.IconButton(saturn.Icons.SHARE), saturn.IconButton(saturn.Icons.DELETE)))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `toggle(self)` | 切换展开与收起状态。 |

## 构造参数

```python
saturn.FloatingToolbar(*items, controls=None, leading=None, trailing=None, expanded=True, vertical=False, vibrant=False, bgcolor=None, elevation=6, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `*items` | `—` | `额外位置参数` | 传给布局、分组或菜单的项目列表。 |
| `controls` | `—` | `None` | 按顺序排列的子控件列表。 |
| `leading` | `—` | `None` | 放在主要内容前面的控件或区域。 |
| `trailing` | `—` | `None` | 放在主要内容后面的控件或区域。 |
| `expanded` | `—` | `True` | 浮动组件或菜单当前是否展开。 |
| `vertical` | `—` | `False` | 为 True 时采用竖向布局。 |
| `vibrant` | `—` | `False` | 工具栏是否采用更鲜明的表面配色。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `elevation` | `—` | `6` | 表面高度，对应阴影的视觉强度。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
