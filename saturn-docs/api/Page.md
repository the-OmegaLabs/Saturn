# Page

应用页面，管理控件树、主题和对话框。

[← API 索引](./README.md)

源码：[`saturn/page.py`](../../saturn/page.py)（第 165 行）。

**基类：** [Control](./Control.md)

## 构造

```python
ft.Page(app)
```

> 这些对象通常由 `ft.run()` 创建和传入，应用代码无需直接构造。

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `app` | `—` | `必填` |

## 本类属性

`bgcolor`、`controls`、`dark_theme`、`fonts`、`height`、`horizontal_alignment`、`overlay`、`padding`、`services`、`spacing`、`theme`、`theme_mode`、`title`、`vertical_alignment`、`width`、`window`。

## 事件回调

`on_keyboard_event`、`on_resize`。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `add(self, *ctrls: 'Control')` | — |
| `insert(self, index, ctrl)` | — |
| `remove(self, ctrl)` | — |
| `remove_at(self, index)` | — |
| `clean(self)` | — |
| `show_dialog(self, dialog)` | — |
| `pop_dialog(self, dialog=None)` | — |
| `update(self)` | — |
| `run_task(self, handler, *args)` | flet run_task: schedule a coroutine handler on the app's loop. |
| `take_screenshot(self, path: 'str | None' = None)` | flet-style async screenshot; returns the frame surface (and saves |
| `draw(self)` | — |
| `handle_event(self, e)` | — |
| `focus(self, control)` | — |
| `pointer_down(self, x, y, clicks=None)` | — |
| `pointer_up(self, x, y)` | — |
| `pointer_move(self, x, y)` | — |

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
