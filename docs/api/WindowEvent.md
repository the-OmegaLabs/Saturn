# WindowEvent

Native desktop window state event with its owning Page.

[← API index](./README.md)

Source: [`saturn/window.py`](../../saturn/window.py) (line 45).

## Constructor parameters

```python
saturn.WindowEvent(control: "'Window'", type: 'WindowEventType') -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `control` | `Window` | `required` | Control that produced the event or holds the data. |
| `type` | `WindowEventType` | `required` | The kind of native window event. |
