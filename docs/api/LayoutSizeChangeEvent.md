# LayoutSizeChangeEvent

LayoutSizeChangeEvent(name: 'str', control: "'Control'", data: 'Any' = None, width: 'float' = 0, height: 'float' = 0)

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 50).

**Base class:** [ControlEvent](./ControlEvent.md)

## Constructor parameters

```python
saturn.LayoutSizeChangeEvent(name: 'str', control: "'Control'", data: 'Any' = None, width: 'float' = 0, height: 'float' = 0) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Name of the object, file, or resource. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
| `width` | `float` | `0` | Specified control width. |
| `height` | `float` | `0` | Specified control height. |
