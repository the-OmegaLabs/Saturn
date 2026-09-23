# ExtendedFloatingActionButton

同时显示图标与文字的浮动操作按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/fab.py`](../../saturn/widgets/fab.py)（第 160 行）。

## 效果图

![ExtendedFloatingActionButton 控件的深色主题效果](../images/controls/ExtendedFloatingActionButton.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ExtendedFloatingActionButton("New document", icon=saturn.Icons.ADD))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [FloatingActionButton](./FloatingActionButton.md)

## 构造参数

```python
saturn.ExtendedFloatingActionButton(text: 'str', *, icon=None, size: 'str' = 'standard', **kwargs)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `text` | `str` | `必填` | 显示在控件上的文字。 |
| `icon` | `—` | `None` | 要绘制的图标。 |
| `size` | `str` | `'standard'` | 文字、图标或控件的尺寸等级。 |
| `**kwargs` | `—` | `额外关键字参数` | 传给父类构造函数的关键字参数。 |
