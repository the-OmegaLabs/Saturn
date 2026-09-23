# Animation

Duration and curve for a property change animation.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 158).

## Constructor parameters

```python
saturn.Animation(duration: 'object' = <factory>, curve: 'AnimationCurve' = <AnimationCurve.LINEAR: 'linear'>) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `duration` | `object` | `<factory>` | Duration; the unit depends on the relevant class. |
| `curve` | `AnimationCurve` | `<AnimationCurve.LINEAR: 'linear'>` | Curve used for animation interpolation. |
