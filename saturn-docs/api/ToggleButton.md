# ToggleButton

可在选中与未选中状态间切换的按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/toggle_button.py`](../../saturn/widgets/toggle_button.py)（第 15 行）。

## 效果图

![ToggleButton 控件的深色主题效果](../images/controls/ToggleButton.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ToggleButton("Selected", checked=True))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [ExpressiveButton](./ExpressiveButton.md)

## 构造参数

```python
saturn.ToggleButton(content=None, *, checked=False, on_change=None, variant='filled', size='small', **kwargs)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `content` | `—` | `None` | 要显示的文本或子控件。 |
| `checked` | `—` | `False` | 切换按钮当前是否处于选中状态。 |
| `on_change` | `—` | `None` | 值改变时调用的回调。 |
| `variant` | `—` | `'filled'` | 选择该控件的视觉变体。 |
| `size` | `—` | `'small'` | 文字、图标或控件的尺寸等级。 |
| `**kwargs` | `—` | `额外关键字参数` | 传给父类构造函数的关键字参数。 |
