# FloatingActionButtonMenuItem

浮动操作菜单中的一个可点击项目。

[← API 索引](./README.md)

源码：[`saturn/widgets/floating.py`](../../saturn/widgets/floating.py)（第 139 行）。

## 效果图

![FloatingActionButtonMenuItem 控件的深色主题效果](../images/controls/FloatingActionButtonMenuItem.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.FloatingActionButtonMenu([saturn.FloatingActionButtonMenuItem("Upload", icon=saturn.Icons.UPLOAD)], expanded=True))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [ExpressiveButton](./ExpressiveButton.md)

## 构造参数

```python
saturn.FloatingActionButtonMenuItem(content, *, icon=None, on_click=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `content` | `—` | `必填` | 要显示的文本或子控件。 |
| `icon` | `—` | `None` | 要绘制的图标。 |
| `on_click` | `—` | `None` | 点击控件时调用的回调。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
