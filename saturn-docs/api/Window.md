# Window

Native window size, title, and state.

[← API index](./README.md)

Source: [`saturn/page.py`](../../saturn/page.py) (line 46).

> `saturn.run()` usually creates and passes these objects; application code does not need to construct them directly.

## Public methods

| Method | Description |
| --- | --- |
| `close(self)` | Closes a window or expanded menu. |
| `destroy(self)` | Destroys the native window and releases resources. |
| `center(self)` | Creates a centered alignment value. |

## Constructor parameters

```python
saturn.Window(app)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `app` | `—` | `required` | Current application instance supplied by the runtime. |
