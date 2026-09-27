# PlatformBrightnessChangeEvent

System light/dark preference supplied to a Page brightness handler.

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 39).

**Base class:** [ControlEvent](./ControlEvent.md)

## Constructor parameters

```python
saturn.PlatformBrightnessChangeEvent(name: 'str', control: "'Control'", data: 'Any' = None, brightness: 'str' = 'light') -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Event name: platform_brightness_change. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
| `brightness` | `str` | `'light'` | Current system or native title-bar brightness: light or dark. |
