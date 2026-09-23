# Icon

显示 Material 图标。

[← API 索引](./README.md)

源码：[`saturn/widgets/basic.py`](../../saturn/widgets/basic.py)（第 50 行）。

## 效果图

![Icon 控件的深色主题效果](../images/controls/Icon.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.Icon(saturn.Icons.FAVORITE, size=56, color=saturn.Colors.PRIMARY))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.Icon(icon, *, color=None, size: 'float' = 24, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `icon` | `—` | `必填` | 要绘制的图标。 |
| `color` | `—` | `None` | 前景、文字或绘制内容的颜色。 |
| `size` | `float` | `24` | 文字、图标或控件的尺寸等级。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
