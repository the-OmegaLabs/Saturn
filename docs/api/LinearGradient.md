# LinearGradient

LinearGradient(colors: 'list', begin: 'Alignment' = <factory>, end: 'Alignment' = <factory>, stops: 'list | None' = None)

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 474).

## Constructor parameters

```python
saturn.LinearGradient(colors: 'list', begin: 'Alignment' = <factory>, end: 'Alignment' = <factory>, stops: 'list | None' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `colors` | `list` | `required` | Ordered colors along the gradient. |
| `begin` | `Alignment` | `<factory>` | Gradient start Alignment. |
| `end` | `Alignment` | `<factory>` | Gradient end Alignment. |
| `stops` | `list | None` | `None` | Optional ascending normalized positions of gradient colors. |
