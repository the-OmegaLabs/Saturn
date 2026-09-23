# Option

Short alias for DropdownOption.

[← API index](./README.md)

Source: [`saturn/widgets/inputs.py`](../../saturn/widgets/inputs.py) (line 1386).

**Base class:** [Control](./Control.md)

The public name `saturn.Option` refers to the implementation class `DropdownOption`.

## Constructor parameters

```python
saturn.Option(key=None, *, text=None, content=None, **base)
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `key` | `—` | `None` | Key used to locate a control or service. |
| `text` | `—` | `None` | Text displayed on the control. |
| `content` | `—` | `None` | Text or child control to display. |
| `**base` | `—` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
