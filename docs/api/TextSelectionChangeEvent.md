# TextSelectionChangeEvent

TextSelectionChangeEvent(name: 'str', control: "'Control'", data: 'Any' = None, selection: 'object' = None, text: 'str' = '')

[← API index](./README.md)

Source: [`saturn/event.py`](../../saturn/event.py) (line 44).

**Base class:** [ControlEvent](./ControlEvent.md)

## Constructor parameters

```python
saturn.TextSelectionChangeEvent(name: 'str', control: "'Control'", data: 'Any' = None, selection: 'object' = None, text: 'str' = '') -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `name` | `str` | `required` | Name of the object, file, or resource. |
| `control` | `Control` | `required` | Control that produced the event or holds the data. |
| `data` | `Any` | `None` | Custom data attached to the control or event. |
| `selection` | `object` | `None` | TextSelection holding the selected character endpoints. |
| `text` | `str` | `''` | Text displayed on the control. |
