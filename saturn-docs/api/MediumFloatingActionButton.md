# MediumFloatingActionButton

中尺寸浮动操作按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/fab.py`](../../saturn/widgets/fab.py)（第 150 行）。

## 效果图

![MediumFloatingActionButton 控件的深色主题效果](../images/controls/MediumFloatingActionButton.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.MediumFloatingActionButton(saturn.Icons.ADD))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [FloatingActionButton](./FloatingActionButton.md)

## 构造参数

```python
saturn.MediumFloatingActionButton(icon=None, **kwargs)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `icon` | `—` | `None` | 要绘制的图标。 |
| `**kwargs` | `—` | `额外关键字参数` | 传给父类构造函数的关键字参数。 |
