# SplitButton

把主操作和副操作分开的按钮。

[← API 索引](./README.md)

源码：[`saturn/widgets/split_button.py`](../../saturn/widgets/split_button.py)（第 106 行）。

## 效果图

![SplitButton 控件的深色主题效果](../images/controls/SplitButton.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.SplitButton("Run", icon=saturn.Icons.PLAY_ARROW))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.SplitButton(content: 'str' = '', *, icon=None, trailing_icon=<Icons.ARROW_DROP_DOWN: 58821>, on_click=None, on_trailing_click=None, bgcolor=None, color=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `content` | `str` | `''` | 要显示的文本或子控件。 |
| `icon` | `—` | `None` | 要绘制的图标。 |
| `trailing_icon` | `—` | `<Icons.ARROW_DROP_DOWN: 58821>` | 分段按钮副操作区域的图标。 |
| `on_click` | `—` | `None` | 点击控件时调用的回调。 |
| `on_trailing_click` | `—` | `None` | 点击分段按钮副操作区域时调用的回调。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `color` | `—` | `None` | 前景、文字或绘制内容的颜色。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
