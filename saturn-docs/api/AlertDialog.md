# AlertDialog

在页面上显示模态对话框。

[← API 索引](./README.md)

源码：[`saturn/widgets/dialogs.py`](../../saturn/widgets/dialogs.py)（第 69 行）。

## 效果图

![AlertDialog 控件的深色主题效果](../images/controls/AlertDialog.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.show_dialog(saturn.AlertDialog(title="Delete item?", content=saturn.Text("This action cannot be undone."), actions=[saturn.TextButton("Cancel"), saturn.FilledButton("Delete")]))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** `DialogControl`

## 构造参数

```python
saturn.AlertDialog(title=None, content=None, *, actions=None, modal=False, bgcolor=None, open=False, on_dismiss=None, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `title` | `—` | `None` | 对话框、提示或窗口的标题。 |
| `content` | `—` | `None` | 要显示的文本或子控件。 |
| `actions` | `—` | `None` | 对话框底部的操作按钮列表。 |
| `modal` | `—` | `False` | 为 True 时禁止点击遮罩关闭对话框。 |
| `bgcolor` | `—` | `None` | 控件或容器的背景颜色。 |
| `open` | `—` | `False` | 对话框或提示条当前是否处于打开状态。 |
| `on_dismiss` | `—` | `None` | 对话框或提示条关闭时调用的回调。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
