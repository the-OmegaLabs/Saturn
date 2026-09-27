# RenderFailedEvent

Reports a failed GPU startup request and recovery to software rendering.

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 61).

**Base class:** [ControlEvent](./ControlEvent.md)

## Constructor parameters

```python
saturn.RenderFailedEvent(name: 'str', control: "'Control'", data: 'Any' = None, backend: 'str' = '', gpu: 'str | int | None' = None, error: 'str' = '', message: 'str' = "Saturn can't use your current GPU, fallback to software renderer.", fallback: 'str' = 'software') -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Event name: render_failed. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
| `backend` | `str` | `''` | Requested GPU backend that failed to initialize. |
| `gpu` | `str | int | None` | `None` | Requested GPU name or index; None means the default device. |
| `error` | `str` | `''` | Error message when an operation fails. |
| `message` | `str` | `"Saturn can't use your current GPU, fallback to software renderer."` | Text of the event or result message. |
| `fallback` | `str` | `'software'` | Recovery backend name: software. |
