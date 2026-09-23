# ControlEvent

Event data received by a control callback.

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 13).

## Constructor parameters

```python
saturn.ControlEvent(name: 'str', control: "'Control'", data: 'Any' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Name of the object, file, or resource. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
