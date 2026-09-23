# Scale

Horizontal and vertical scale of a control.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 324).

## Constructor parameters

```python
saturn.Scale(scale: 'float | None' = None, scale_x: 'float | None' = None, scale_y: 'float | None' = None, alignment: 'Alignment | None' = None, origin: 'Offset | None' = None, transform_hit_tests: 'bool' = True, filter_quality: 'object' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `scale` | `float | None` | `None` | Scale applied when drawing the control. |
| `scale_x` | `float | None` | `None` | Horizontal scale factor. |
| `scale_y` | `float | None` | `None` | Vertical scale factor. |
| `alignment` | `Alignment | None` | `None` | Alignment of child content within a container or layout. |
| `origin` | `Offset | None` | `None` | Reference origin for the transformation. |
| `transform_hit_tests` | `bool` | `True` | Apply the geometry transform to the hit area as well. |
| `filter_quality` | `object` | `None` | Sampling quality used when scaling an image. |
