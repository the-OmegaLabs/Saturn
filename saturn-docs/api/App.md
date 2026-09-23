# App

管理窗口、事件循环和绘制后端的应用对象。

[← API 索引](./README.md)

源码：[`saturn/app.py`](../../saturn/app.py)（第 113 行）。

## 构造

```python
ft.App(main, backend: 'Render', width: 'int', height: 'int', title: 'str')
```

> 这些对象通常由 `ft.run()` 创建和传入，应用代码无需直接构造。

### 参数

| 参数 | 类型标注 | 默认值 |
| --- | --- | --- |
| `main` | `—` | `必填` |
| `backend` | `Render` | `必填` |
| `width` | `int` | `必填` |
| `height` | `int` | `必填` |
| `title` | `str` | `必填` |

## 本类属性

`outer_size`、`page`、`pixel_ratio`、`refresh_rate`、`renderer`、`size`。

## 本类公开方法

| 方法 | 说明 |
| --- | --- |
| `start(self)` | — |
| `close(self)` | — |
| `run_until_closed(self)` | — |
| `call(self, fn, *args)` | Run a user callable off the UI thread (sync: thread, async: loop). |
| `mark_dirty(self)` | — |
| `post(self, fn)` | Run a callable on the UI thread (required for SDL display calls). |
| `set_text_input_rect(self, rect: 'pygame.Rect')` | Position SDL text input using a caret-relative exclusion area. |
| `screenshot(self, path: 'str | None' = None)` | Grab the current frame from any thread; returns a pygame Surface |
| `physical_size_for_logical(self, width, height)` | — |
| `logical_point(self, x, y)` | — |
| `client_size_for_outer(self, width, height)` | — |

---

本页依据仓库当前公开 API 与源码生成。继承成员请查阅基类；参数表中的 `**base` 会传给基类。
