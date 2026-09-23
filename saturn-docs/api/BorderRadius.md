# BorderRadius

Corner radii for each of the four corners.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 246).

## Public methods

| Method | Description |
| --- | --- |
| `all(cls, radius: 'float')` | Creates the same setting for every side. |
| `horizontal(cls, left: 'float' = 0.0, right: 'float' = 0.0)` | Sets the two horizontal values. |
| `vertical(cls, top: 'float' = 0.0, bottom: 'float' = 0.0)` | Sets the two vertical values. |
| `only(cls, top_left: 'float' = 0.0, top_right: 'float' = 0.0, bottom_right: 'float' = 0.0, bottom_left: 'float' = 0.0)` | Sets values for specified sides individually. |

## Constructor parameters

```python
saturn.BorderRadius(top_left: 'float' = 0.0, top_right: 'float' = 0.0, bottom_right: 'float' = 0.0, bottom_left: 'float' = 0.0) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `top_left` | `float` | `0.0` | Corner radius at the top left. |
| `top_right` | `float` | `0.0` | Corner radius at the top right. |
| `bottom_right` | `float` | `0.0` | Corner radius at the bottom right. |
| `bottom_left` | `float` | `0.0` | Corner radius at the bottom left. |
