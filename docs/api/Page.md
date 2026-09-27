# Page

Application page that manages controls, themes, and dialogs.

[← API index](./README.md)

Source: [`saturn/page.py`](../../saturn/page.py) (line 88).

**Base class:** [Control](./Control.md)

## Renderer settings

`page.renderer.anti_aliasing` and `page.renderer.vsync` are boolean settings
that default to `True`. `page.renderer.context` exposes the active backend renderer.
`page.renderer.name` reports `software`, `opengl` or `vulkan`, or `None` before startup.
See [Renderer settings](../rendering.md) for backend behavior and threading rules.

See [Page fonts and events](../page.md) for font registration, typed callbacks, themes, and ownership.

> `saturn.run()` usually creates and passes these objects; application code does not need to construct them directly.

## Public methods

| Method | Description |
| --- | --- |
| `go(self, route)` | Set the application route and notify each window's route handler. |
| `open_subpage(self, main=None, *, title='Settings', modal=False, anchor='center', offset=None, follow_parent=False, backend=None)` | Create an owned native child window and return its Subpage handle. |
| `add(self, *ctrls: 'Control')` | Adds a child control to the end of a page or control list. |
| `insert(self, index, ctrl)` | Inserts a child control at a specified position. |
| `remove(self, ctrl)` | Removes a specified control from its container. |
| `remove_at(self, index)` | Removes a child control by index. |
| `clean(self)` | Removes all regular controls from the page. |
| `show_dialog(self, dialog)` | Shows a dialog or snackbar on the page. |
| `pop_dialog(self, dialog=None)` | Closes the current dialog or snackbar. |
| `update(self)` | Requests a redraw of this control and its changes. |
| `repaint(self)` | Redraw when geometry has not changed (scroll, hover, ripple). |
| `run_task(self, handler, *args)` | Schedule a coroutine handler on the application event loop. |
| `take_screenshot(self, path: 'str | None' = None)` | Return the captured frame surface (and save |
| `draw(self)` | Requests a draw of the current page. |
| `handle_event(self, e)` | Handles an incoming control event. |
| `focus(self, control)` | Focus this attached control when keyboard focus is enabled. |
| `pointer_down(self, x, y, clicks=None)` | Handles a pointer press. |
| `pointer_up(self, x, y)` | Handles a pointer release. |
| `pointer_move(self, x, y)` | Handles pointer movement. |

## Constructor parameters

```python
saturn.Page(app)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `app` | `—` | `required` | Current application instance supplied by the runtime. |
