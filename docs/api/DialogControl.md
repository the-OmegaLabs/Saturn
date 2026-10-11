# DialogControl

Base: fills the page as an overlay; card area is interactive.

[← API index](./README.md)

Source: [`saturn/widgets/dialogs.py`](../../saturn/widgets/dialogs.py) (line 30).

**Base class:** [Control](./Control.md)

## Constructor parameters

```python
saturn.DialogControl(*, open: 'bool' = False, modal: 'bool' = False, on_dismiss=None, **base: 'Unpack[ControlOptions]')
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `open` | `bool` | `False` | Whether the dialog or snackbar is open. |
| `modal` | `bool` | `False` | Prevent closing the dialog by clicking its barrier when True. |
| `on_dismiss` | `—` | `None` | Callback called when the dialog or snackbar closes. |
| `**base` | `Unpack[ControlOptions]` | `additional keyword arguments` | Keyword arguments passed to Control, such as width and height. |

`**base` accepts [common Control constructor parameters](./Control.md#constructor-parameters), such as `width`, `height`, and `visible`.
