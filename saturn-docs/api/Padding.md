# Padding

Space inside a control on each side.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 217).

## Public methods

| Method | Description |
| --- | --- |
| `all(cls, value: 'float')` | Creates the same setting for every side. |
| `symmetric(cls, vertical: 'float' = 0.0, horizontal: 'float' = 0.0)` | Sets symmetric horizontal and vertical values. |
| `only(cls, left: 'float' = 0.0, top: 'float' = 0.0, right: 'float' = 0.0, bottom: 'float' = 0.0)` | Sets values for specified sides individually. |
| `zero(cls)` | Creates a setting with zero on all four sides. |

## Constructor parameters

```python
saturn.Padding(left: 'float' = 0.0, top: 'float' = 0.0, right: 'float' = 0.0, bottom: 'float' = 0.0) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `left` | `float` | `0.0` | Distance from the left edge of a Stack. |
| `top` | `float` | `0.0` | Distance from the top edge of a Stack. |
| `right` | `float` | `0.0` | Distance from the right edge of a Stack. |
| `bottom` | `float` | `0.0` | Distance from the bottom edge of a Stack. |
