# VerticalFloatingToolbar

纵向排列操作的浮动工具栏。

[← API 索引](./README.md)

源码：[`saturn/widgets/floating.py`](../../saturn/widgets/floating.py)（第 134 行）。

## 效果图

![VerticalFloatingToolbar 控件的深色主题效果](../images/controls/VerticalFloatingToolbar.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.VerticalFloatingToolbar(saturn.IconButton(saturn.Icons.EDIT), saturn.IconButton(saturn.Icons.DELETE)))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [FloatingToolbar](./FloatingToolbar.md)

## 构造参数

```python
saturn.VerticalFloatingToolbar(*items, **kwargs)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `*items` | `—` | `额外位置参数` | 传给布局、分组或菜单的项目列表。 |
| `**kwargs` | `—` | `额外关键字参数` | 传给父类构造函数的关键字参数。 |
