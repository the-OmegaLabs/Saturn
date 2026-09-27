# RouteChangeEvent

RouteChangeEvent(name: 'str', control: "'Control'", data: 'Any' = None, route: 'str' = '/')

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 56).

**Base class:** [ControlEvent](./ControlEvent.md)

## Constructor parameters

```python
saturn.RouteChangeEvent(name: 'str', control: "'Control'", data: 'Any' = None, route: 'str' = '/') -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Name of the object, file, or resource. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
| `route` | `str` | `'/'` | Application route string shared by its native windows. |
