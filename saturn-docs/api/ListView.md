# ListView

可滚动的控件列表。

[← API 索引](./README.md)

源码：[`saturn/widgets/scrolling.py`](../../saturn/widgets/scrolling.py)（第 27 行）。

## 效果图

![ListView 控件的深色主题效果](../images/controls/ListView.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ListView([saturn.Text(f"Item {i}") for i in range(1, 6)], spacing=12, width=320, height=180))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `scroll_to(self, offset: 'float' = 0, delta: 'float | None' = None)` | 滚动到指定位置或按给定距离滚动。 |

## 构造参数

```python
saturn.ListView(*items, controls=None, horizontal: 'bool' = False, spacing: 'float' = 0, padding=None, auto_scroll: 'bool' = False, on_scroll=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `*items` | `—` | `额外位置参数` | 传给布局、分组或菜单的项目列表。 |
| `controls` | `—` | `None` | 按顺序排列的子控件列表。 |
| `horizontal` | `bool` | `False` | 为 True 时采用水平滚动或水平排布。 |
| `spacing` | `float` | `0` | 相邻子控件之间的间距。 |
| `padding` | `—` | `None` | 控件内容四周的内边距。 |
| `auto_scroll` | `bool` | `False` | 内容增加时是否自动滚动到末尾。 |
| `on_scroll` | `—` | `None` | 列表滚动时调用的回调。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
