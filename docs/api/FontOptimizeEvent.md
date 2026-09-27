# FontOptimizeEvent

Reports background font load/weight optimization start, completion or failure.

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 78).

**Base class:** [ControlEvent](./ControlEvent.md)

## Constructor parameters

```python
saturn.FontOptimizeEvent(name: 'str', control: "'Control'", data: 'Any' = None, font: 'str' = '', weight: 'int | None' = None, status: 'str' = 'started', success: 'bool | None' = None, error: 'str | None' = None, operation: 'str' = 'instance', cached: 'bool' = False) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Event name: font_optimize. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
| `font` | `str` | `''` | Font source being downloaded or instanced. |
| `weight` | `int | None` | `None` | Requested numeric weight for instancing; None for font downloads. |
| `status` | `str` | `'started'` | Background operation phase: started, completed or failed. |
| `success` | `bool | None` | `None` | None when work starts; True on completion or False on failure. |
| `error` | `str | None` | `None` | Error message when an operation fails. |
| `operation` | `str` | `'instance'` | Background font operation: load or instance. |
| `cached` | `bool` | `False` | Whether the completed font result was persisted to disk. |
