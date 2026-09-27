# PageResizeEvent

Logical client dimensions supplied to a Page resize handler.

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 24).

**Base class:** [ControlEvent](./ControlEvent.md)

## Constructor parameters

```python
saturn.PageResizeEvent(name: 'str', control: "'Control'", data: 'Any' = None, width: 'float' = 0, height: 'float' = 0) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Event name: resize. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
| `width` | `float` | `0` | Logical client width after resizing. |
| `height` | `float` | `0` | Logical client height after resizing. |
