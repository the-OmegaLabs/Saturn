# RenderReadyEvent

Reports the actual backend and GPU after initialization or software recovery.

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 70).

**Base class:** [ControlEvent](./ControlEvent.md)

## Constructor parameters

```python
saturn.RenderReadyEvent(name: 'str', control: "'Control'", data: 'Any' = None, backend: 'str' = '', gpu_name: 'str | None' = None, gpu_index: 'int | None' = None, fallback: 'bool' = False) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Event name: render_ready. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
| `backend` | `str` | `''` | Actual initialized backend: opengl, vulkan or software. |
| `gpu_name` | `str | None` | `None` | Actual GPU renderer model; None for software rendering. |
| `gpu_index` | `int | None` | `None` | Actual device index in the active renderer's available devices; None when unavailable. |
| `fallback` | `bool` | `False` | True if GPU initialization failed and this window recovered to software. |
