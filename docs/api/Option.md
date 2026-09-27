# Option

Short alias for DropdownOption.

[← API index](./README.md)

Source: [`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py) (line 2014).

**Base class:** [Control](./Control.md)

The public name `saturn.Option` refers to the implementation class `DropdownOption`.

## Constructor parameters

```python
saturn.Option(key=None, *, text=None, content=None, leading_icon=None, trailing_icon=None, style=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `key` | `—` | `None` | Application key identifying the control or option. |
| `text` | `—` | `None` | Text displayed on the control. |
| `content` | `—` | `None` | Text or child control to display. |
| `leading_icon` | `—` | `None` | Icon used for leading. |
| `trailing_icon` | `—` | `None` | Icon in the secondary action area of a split button. |
| `style` | `—` | `None` | Additional button style settings. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
