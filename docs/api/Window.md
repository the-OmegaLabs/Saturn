# Window

Native desktop window properties, events, and operating-system handles.

[← API index](./README.md)

Source: [`saturn/window.py`](../../saturn/window.py) (line 125).

See [Native desktop windows](../window.md) for property behavior, platform limits, handles, and close interception.

> `saturn.run()` usually creates and passes these objects; application code does not need to construct them directly.

## Public methods

| Method | Description |
| --- | --- |
| `close(self)` | Request closing; respects prevent_close and emits CLOSE. |
| `destroy(self)` | Force application shutdown even when prevent_close is set. |
| `center(self)` | Queue centering within the nearest monitor's work area. |
| `wait_until_ready_to_show(self)` | Wait until earlier UI queue operations have completed. |
| `to_front(self)` | Queue native window activation. |
| `start_dragging(self)` | Begin native Windows caption dragging when movement is enabled. |
| `start_resizing(self, edge)` | Begin native Windows resizing at the requested edge. |

## Constructor parameters

```python
saturn.Window(app)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `app` | `—` | `required` | Current application instance supplied by the runtime. |
