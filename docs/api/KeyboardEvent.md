# KeyboardEvent

Pressed key and modifier flags supplied to a Page keyboard handler.

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 30).

**Base class:** [ControlEvent](./ControlEvent.md)

## Constructor parameters

```python
saturn.KeyboardEvent(name: 'str', control: "'Control'", data: 'Any' = None, key: 'str' = '', shift: 'bool' = False, ctrl: 'bool' = False, alt: 'bool' = False, meta: 'bool' = False) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Event name: keyboard_event. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
| `key` | `str` | `''` | Pressed key name, such as S, Enter, or Arrow Left. |
| `shift` | `bool` | `False` | Whether the Shift modifier was pressed for this event. |
| `ctrl` | `bool` | `False` | Whether the Control modifier was pressed for this event. |
| `alt` | `bool` | `False` | Whether the Alt modifier was pressed for this event. |
| `meta` | `bool` | `False` | Whether the platform Meta modifier was pressed for this event. |
