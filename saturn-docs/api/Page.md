# Page

应用页面，管理控件树、主题和对话框。

[← API 索引](./README.md)

源码：[`saturn/page.py`](../../saturn/page.py)（第 165 行）。

**基类：** [Control](./Control.md)

> 这些对象通常由 `saturn.run()` 创建和传入，应用代码无需直接构造。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `add(self, *ctrls: 'Control')` | 在页面或控件列表末尾加入子控件。 |
| `insert(self, index, ctrl)` | 在指定位置插入子控件。 |
| `remove(self, ctrl)` | 从容器中移除指定控件。 |
| `remove_at(self, index)` | 按索引移除子控件。 |
| `clean(self)` | 移除页面中的全部普通控件。 |
| `show_dialog(self, dialog)` | 在页面上显示对话框或提示条。 |
| `pop_dialog(self, dialog=None)` | 关闭当前对话框或提示条。 |
| `update(self)` | 请求重绘本控件及其变化。 |
| `run_task(self, handler, *args)` | flet run_task: schedule a coroutine handler on the app's loop. |
| `take_screenshot(self, path: 'str | None' = None)` | flet-style async screenshot; returns the frame surface (and saves |
| `draw(self)` | 请求绘制当前页面内容。 |
| `handle_event(self, e)` | 处理传入的控件事件。 |
| `focus(self, control)` | 使控件获得输入焦点。 |
| `pointer_down(self, x, y, clicks=None)` | 处理指针按下事件。 |
| `pointer_up(self, x, y)` | 处理指针松开事件。 |
| `pointer_move(self, x, y)` | 处理指针移动事件。 |

## 构造参数

```python
saturn.Page(app)
```

| 参数 | 类型标注 | 默认值 | 作用 |
| --- | --- | --- | --- |
| `app` | `—` | `必填` | 当前应用实例，由运行时传入。 |
