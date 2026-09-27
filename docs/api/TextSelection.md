# TextSelection

TextSelection(base_offset: 'int' = 0, extent_offset: 'int' = 0, affinity: 'TextAffinity' = <TextAffinity.DOWNSTREAM: 'downstream'>, directional: 'bool' = False)

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 499).

## Constructor parameters

```python
saturn.TextSelection(base_offset: 'int' = 0, extent_offset: 'int' = 0, affinity: 'TextAffinity' = <TextAffinity.DOWNSTREAM: 'downstream'>, directional: 'bool' = False) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `base_offset` | `int` | `0` | Starting character offset of a selection. |
| `extent_offset` | `int` | `0` | Ending character offset of a selection. |
| `affinity` | `TextAffinity` | `<TextAffinity.DOWNSTREAM: 'downstream'>` | Selection affinity at a line boundary. |
| `directional` | `bool` | `False` | Whether selection direction is significant. |
