# App

Application object that manages windows, events, and rendering.

[← API index](./README.md)

Source: [`saturn/app.py`](../../saturn/app.py) (line 113).

> `saturn.run()` usually creates and passes these objects; application code does not need to construct them directly.

## Public methods

| Method | Description |
| --- | --- |
| `start(self)` | Starts the application window and event handling. |
| `close(self)` | Closes a window or expanded menu. |
| `run_until_closed(self)` | Processes window events until the window closes. |
| `call(self, fn, *args)` | Run a user callable off the UI thread (sync: thread, async: loop). |
| `mark_dirty(self)` | Marks the interface for redrawing. |
| `post(self, fn)` | Run a callable on the UI thread (required for SDL display calls). |
| `set_text_input_rect(self, rect: 'pygame.Rect')` | Position SDL text input using a caret-relative exclusion area. |
| `screenshot(self, path: 'str | None' = None)` | Grab the current frame from any thread; returns a pygame Surface |
| `physical_size_for_logical(self, width, height)` | Converts logical dimensions to physical pixels. |
| `logical_point(self, x, y)` | Converts physical coordinates to logical coordinates. |
| `client_size_for_outer(self, width, height)` | Converts outer window dimensions to client area dimensions. |

## Constructor parameters

```python
saturn.App(main, backend: 'Render', width: 'int', height: 'int', title: 'str')
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `main` | `—` | `required` | Application entry point that receives a Page. |
| `backend` | `Render` | `required` | Rendering backend to use. |
| `width` | `int` | `required` | Specified control width. |
| `height` | `int` | `required` | Specified control height. |
| `title` | `str` | `required` | Title of a dialog, notification, or window. |
