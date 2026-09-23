# SnackBar

显示短暂的操作反馈。

[← API 索引](./README.md)

源码：[`saturn/widgets/dialogs.py`](../../saturn/widgets/dialogs.py)（第 227 行）。

## 效果图

![SnackBar 控件的深色主题效果](../images/controls/SnackBar.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.show_dialog(saturn.SnackBar(saturn.Text("Saved successfully", color=saturn.Colors.ON_SURFACE), action="Undo", bgcolor=saturn.Colors.SURFACE_CONTAINER, duration=10000))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** `DialogControl`

## 构造参数

```python
saturn.SnackBar(content, *, action=None, bgcolor=None, duration: 'int' = 4000, on_action=None, open=False, on_dismiss=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `content` | `—` | `必填` | 要显示的文本或子控件。 |
| `action` | `—` | `None` | 提示条上的单个操作文本或按钮。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `duration` | `int` | `4000` | 提示条显示的毫秒数。 |
| `on_action` | `—` | `None` | 点击提示条操作时调用的回调。 |
| `open` | `—` | `False` | 对话框或提示条当前是否处于打开状态。 |
| `on_dismiss` | `—` | `None` | 对话框或提示条关闭时调用的回调。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
