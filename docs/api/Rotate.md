# Rotate

Rotation angle and center of a control.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 335).

## Constructor parameters

```python
saturn.Rotate(angle: 'float' = 0.0, alignment: 'Alignment | None' = None, origin: 'Offset | None' = None, transform_hit_tests: 'bool' = True, filter_quality: 'object' = None) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `angle` | `float` | `0.0` | Rotation angle. |
| `alignment` | `Alignment | None` | `None` | Alignment of child content within a container or layout. |
| `origin` | `Offset | None` | `None` | Reference origin for the transformation. |
| `transform_hit_tests` | `bool` | `True` | Apply the geometry transform to the hit area as well. |
| `filter_quality` | `object` | `None` | Sampling quality used when scaling an image. |
