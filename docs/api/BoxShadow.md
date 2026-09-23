# BoxShadow

Spread, blur, color, and offset of a control shadow.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py) (line 344).

## Constructor parameters

```python
saturn.BoxShadow(spread_radius: 'float' = 0.0, blur_radius: 'float' = 0.0, color: 'object' = '#000000', offset: 'Offset' = <factory>) -> None
```

| Parameter | Type annotation | Default | Description |
| --- | --- | --- | --- |
| `spread_radius` | `float` | `0.0` | Distance the shadow outline expands outward. |
| `blur_radius` | `float` | `0.0` | Shadow blur radius. |
| `color` | `object` | `'#000000'` | Color of foreground content, text, or drawing. |
| `offset` | `Offset` | `<factory>` | Displacement applied beyond the layout position. |
