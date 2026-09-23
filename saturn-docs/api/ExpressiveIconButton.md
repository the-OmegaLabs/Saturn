# ExpressiveIconButton

支持 Expressive 尺寸和形状变化的图标按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/buttons.py`](../../saturn/widgets/buttons.py)（第 405 行）。

## 效果图

![ExpressiveIconButton 控件的深色主题效果](../images/controls/ExpressiveIconButton.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.ExpressiveIconButton(saturn.Icons.EDIT, size="large"))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [IconButton](./IconButton.md)

## 构造参数

```python
saturn.ExpressiveIconButton(icon, *, size='small', **kwargs)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `icon` | `—` | `必填` | 要绘制的图标。 |
| `size` | `—` | `'small'` | 文字、图标或控件的尺寸等级。 |
| `**kwargs` | `—` | `额外关键字参数` | 传给父类构造函数的关键字参数。 |
