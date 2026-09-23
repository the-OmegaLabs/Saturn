# App

管理窗口、事件循环和绘制后端的应用对象。

[← API 索引](./README.md)

源码：[`saturn/app.py`](../../saturn/app.py)（第 113 行）。

> 这些对象通常由 `saturn.run()` 创建和传入，应用代码无需直接构造。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `start(self)` | 启动应用窗口与事件处理。 |
| `close(self)` | 关闭窗口或展开的菜单。 |
| `run_until_closed(self)` | 持续处理窗口事件，直到窗口关闭。 |
| `call(self, fn, *args)` | Run a user callable off the UI thread (sync: thread, async: loop). |
| `mark_dirty(self)` | 标记界面需要重新绘制。 |
| `post(self, fn)` | Run a callable on the UI thread (required for SDL display calls). |
| `set_text_input_rect(self, rect: 'pygame.Rect')` | Position SDL text input using a caret-relative exclusion area. |
| `screenshot(self, path: 'str | None' = None)` | Grab the current frame from any thread; returns a pygame Surface |
| `physical_size_for_logical(self, width, height)` | 把逻辑尺寸换算为物理像素尺寸。 |
| `logical_point(self, x, y)` | 把物理坐标换算为逻辑坐标。 |
| `client_size_for_outer(self, width, height)` | 根据窗口外框尺寸换算客户区域尺寸。 |

## 构造参数

```python
saturn.App(main, backend: 'Render', width: 'int', height: 'int', title: 'str')
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `main` | `—` | `必填` | 应用入口函数，接收 Page 对象。 |
| `backend` | `Render` | `必填` | 绘制后端的选择。 |
| `width` | `int` | `必填` | 控件的指定宽度。 |
| `height` | `int` | `必填` | 控件的指定高度。 |
| `title` | `str` | `必填` | 对话框、提示或窗口的标题。 |
