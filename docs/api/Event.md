# Event

ControlEvent(name: 'str', control: "'Control'", data: 'Any' = None)

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 13).

The public name `saturn.Event` refers to the implementation class `ControlEvent`.

## Constructor parameters

```python
saturn.Event(name: 'str', control: "'Control'", data: 'Any' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Name of the object, file, or resource. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
