# ExpressiveButton

支持尺寸和形状变化的 Material Expressive 按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/buttons.py`](../../saturn/widgets/buttons.py)（第 280 行）。

## 效果图

![ExpressiveButton 控件的深色主题效果](../images/controls/ExpressiveButton.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ExpressiveButton("Create", size="medium", icon=saturn.Icons.ADD))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Button](./Button.md)

## 构造参数

```python
saturn.ExpressiveButton(content=None, *, size='small', shape='round', **kwargs)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `content` | `—` | `None` | 要显示的文本或子控件。 |
| `size` | `—` | `'small'` | 文字、图标或控件的尺寸等级。 |
| `shape` | `—` | `'round'` | 按钮的基础形状。 |
| `**kwargs` | `—` | `额外关键字参数` | 传给父类构造函数的关键字参数。 |
