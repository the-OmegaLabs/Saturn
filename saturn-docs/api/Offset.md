# Offset

Two-dimensional displacement and its hit-test behavior.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 316).

## Constructor parameters

```python
saturn.Offset(x: 'float' = 0.0, y: 'float' = 0.0, transform_hit_tests: 'bool' = True, filter_quality: 'object' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `x` | `float` | `0.0` | Horizontal coordinate or displacement. |
| `y` | `float` | `0.0` | Vertical coordinate or displacement. |
| `transform_hit_tests` | `bool` | `True` | Apply the geometry transform to the hit area as well. |
| `filter_quality` | `object` | `None` | Sampling quality used when scaling an image. |
