# Control

Base class for visual controls, with size, state, and update methods.

[← API index](./README.md)

Source: [`saturn/control.py`](../../saturn/control.py) (line 26).

## Public methods

| Method | Description |
| --- | --- |
| `update(self)` | Requests a redraw of this control and its changes. |
| `repaint(self)` | Performs the corresponding operation. |
| `focus(self)` | Focus this attached control when keyboard focus is enabled. |
| `handle_event(self, e) -> 'bool'` | Handles an incoming control event. |

## Constructor parameters

```python
saturn.Control(*, visible: 'bool' = True, disabled: 'bool' = False, opacity: 'float' = 1.0, expand: 'bool | int | None' = None, expand_loose: 'bool' = False, tooltip: 'str | None' = None, data=None, width: 'float | None' = None, height: 'float | None' = None, margin=None, align: 'Alignment | None' = None, left: 'float | None' = None, top: 'float | None' = None, right: 'float | None' = None, bottom: 'float | None' = None, rotate=None, scale=None, offset=None, animate_opacity=None, animate_size=None, animate_position=None, animate_align=None, animate_margin=None, animate_rotation=None, animate_scale=None, animate_offset=None, on_animation_end=None, key=None, ref=None, rtl=None, aspect_ratio=None, mouse_cursor=None, semantics_label=None, can_request_focus=True, on_size_change=None, size_change_interval=10, **unsupported)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `visible` | `bool` | `True` | Hide the control when False. |
| `disabled` | `bool` | `False` | Disable interaction and use the disabled appearance when True. |
| `opacity` | `float` | `1.0` | Control opacity, from 0 (transparent) to 1 (opaque). |
| `expand` | `bool | int | None` | `None` | Fill remaining parent space; a number sets the flex ratio. |
| `expand_loose` | `bool` | `False` | Treat the flex share as a maximum instead of forcing the child to fill it. |
| `tooltip` | `str | None` | `None` | Short hint shown on hover. |
| `data` | `—` | `None` | Custom data attached to the control or event. |
| `width` | `float | None` | `None` | Specified control width. |
| `height` | `float | None` | `None` | Specified control height. |
| `margin` | `—` | `None` | Space outside the control. |
| `align` | `Alignment | None` | `None` | Alignment of the control within the available area. |
| `left` | `float | None` | `None` | Distance from the left edge of a Stack. |
| `top` | `float | None` | `None` | Distance from the top edge of a Stack. |
| `right` | `float | None` | `None` | Distance from the right edge of a Stack. |
| `bottom` | `float | None` | `None` | Distance from the bottom edge of a Stack. |
| `rotate` | `—` | `None` | Rotation applied when drawing the control. |
| `scale` | `—` | `None` | Scale applied when drawing the control. |
| `offset` | `—` | `None` | Displacement applied beyond the layout position. |
| `animate_opacity` | `—` | `None` | Animation settings applied when opacity changes. |
| `animate_size` | `—` | `None` | Animation settings applied when size changes. |
| `animate_position` | `—` | `None` | Animation settings applied when position changes. |
| `animate_align` | `—` | `None` | Animation settings applied when align changes. |
| `animate_margin` | `—` | `None` | Animation settings applied when margin changes. |
| `animate_rotation` | `—` | `None` | Animation settings applied when rotation changes. |
| `animate_scale` | `—` | `None` | Animation settings applied when scale changes. |
| `animate_offset` | `—` | `None` | Animation settings applied when offset changes. |
| `on_animation_end` | `—` | `None` | Callback called when the control animation finishes. |
| `key` | `—` | `None` | Application key identifying the control or option. |
| `ref` | `—` | `None` | Ref whose current property receives this control. |
| `rtl` | `—` | `None` | Right-to-left direction; None inherits the parent's direction. |
| `aspect_ratio` | `—` | `None` | Positive width-to-height ratio fitted within parent constraints. |
| `mouse_cursor` | `—` | `None` | Cursor displayed while hovering over the control. |
| `semantics_label` | `—` | `None` | Accessibility description metadata; native accessibility is not implemented. |
| `can_request_focus` | `—` | `True` | Allow programmatic and keyboard focus when True. |
| `on_size_change` | `—` | `None` | Callback for size change; accepts zero arguments or an event. |
| `size_change_interval` | `—` | `10` | Minimum interval in milliseconds between size events; the final size is delivered. |
| `**unsupported` | `—` | `additional keyword arguments` | Unknown keyword arguments raise TypeError. |
