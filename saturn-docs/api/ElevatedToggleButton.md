# ElevatedToggleButton

带有抬升表面的切换按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/toggle_button.py`](../../saturn/widgets/toggle_button.py)（第 66 行）。

## 效果图

![ElevatedToggleButton 控件的深色主题效果](../images/controls/ElevatedToggleButton.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ElevatedToggleButton("Pinned", checked=True))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [ToggleButton](./ToggleButton.md)

## 构造参数

```python
saturn.ElevatedToggleButton(content=None, **kwargs)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `content` | `—` | `None` | 要显示的文本或子控件。 |
| `**kwargs` | `—` | `额外关键字参数` | 传给父类构造函数的关键字参数。 |
