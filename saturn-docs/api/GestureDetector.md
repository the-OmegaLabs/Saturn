# GestureDetector

接收指针和手势事件。

[← API 索引](./README.md)

源码：[`saturn/widgets/scrolling.py`](../../saturn/widgets/scrolling.py)（第 337 行）。

## 效果图

![GestureDetector 控件的深色主题效果](../images/controls/GestureDetector.png)

## 示例代码

以下代码可从仓库根目录运行，呈现上图中的控件。

```python
import saturn


def main(page: saturn.Page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    page.add(saturn.GestureDetector(saturn.Container(saturn.Text("Tap this surface"), padding=20, bgcolor=saturn.Colors.PRIMARY_CONTAINER, border_radius=12), on_tap=lambda event: None))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE, width=720, height=360)
```

**基类：** [Control](./Control.md)

## 构造参数

```python
saturn.GestureDetector(content=None, *, on_tap=None, on_tap_down=None, on_long_press=None, on_hover=None, on_enter=None, on_exit=None, mouse_cursor=None, drag_interval=0, hover_interval=0, **base)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `content` | `—` | `None` | 要显示的文本或子控件。 |
| `on_tap` | `—` | `None` | 完成轻触操作时调用的回调。 |
| `on_tap_down` | `—` | `None` | 开始按下控件时调用的回调。 |
| `on_long_press` | `—` | `None` | 长按控件时调用的回调。 |
| `on_hover` | `—` | `None` | 指针悬停状态变化时调用的回调。 |
| `on_enter` | `—` | `None` | 指针进入控件区域时调用的回调。 |
| `on_exit` | `—` | `None` | 指针离开控件区域时调用的回调。 |
| `mouse_cursor` | `—` | `None` | 悬停时显示的鼠标指针样式。 |
| `drag_interval` | `—` | `0` | 连续拖动事件的最短触发间隔。 |
| `hover_interval` | `—` | `0` | 连续悬停事件的最短触发间隔。 |
| `**base` | `—` | `额外关键字参数` | 传给基础 Control 构造函数的关键字参数，例如 width、height。 |

`**base` 可传入 [Control 的通用构造参数](./Control.md#构造参数)，例如 `width`、`height`、`visible`。
