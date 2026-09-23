# Tooltip

Configures a hint shown on hover or long press.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 364).

## Constructor parameters

```python
saturn.Tooltip(message: 'str', decoration: 'object' = None, enable_feedback: 'bool | None' = None, vertical_offset: 'float | None' = None, margin: 'object' = None, padding: 'object' = None, bgcolor: 'object' = None, text_style: 'TextStyle | None' = None, text_align: 'TextAlign | None' = None, prefer_below: 'bool | None' = None, show_duration: 'object' = None, wait_duration: 'object' = None, exit_duration: 'object' = None, tap_to_dismiss: 'bool' = True, exclude_from_semantics: 'bool | None' = False, trigger_mode: 'TooltipTriggerMode | None' = None, mouse_cursor: 'object' = None, size_constraints: 'object' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `message` | `str` | `required` | Text of the event or result message. |
| `decoration` | `object` | `None` | Text or border decoration settings. |
| `enable_feedback` | `bool | None` | `None` | Provide interaction feedback when enabled. |
| `vertical_offset` | `float | None` | `None` | Additional vertical displacement. |
| `margin` | `object` | `None` | Space outside the control. |
| `padding` | `object` | `None` | Space around the control's content. |
| `bgcolor` | `object` | `None` | Background color of the control or container. |
| `text_style` | `TextStyle | None` | `None` | Style of entered or displayed text. |
| `text_align` | `TextAlign | None` | `None` | Text alignment within the available width. |
| `prefer_below` | `bool | None` | `None` | Place the tooltip below the control when space permits. |
| `show_duration` | `object` | `None` | Duration of the entrance transition. |
| `wait_duration` | `object` | `None` | Delay before the next display. |
| `exit_duration` | `object` | `None` | Duration of the exit transition. |
| `tap_to_dismiss` | `bool` | `True` | Dismiss the tooltip when its area is tapped. |
| `exclude_from_semantics` | `bool | None` | `False` | Exclude this control from accessibility semantics. |
| `trigger_mode` | `TooltipTriggerMode | None` | `None` | Interaction that triggers the tooltip. |
| `mouse_cursor` | `object` | `None` | Pointer style shown on hover. |
| `size_constraints` | `object` | `None` | Allowed minimum and maximum dimensions. |
