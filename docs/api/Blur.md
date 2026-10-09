# Blur

Gaussian blur sigmas for Container.blur (Flet-compatible).

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py).

**Constructor:**

```python
saturn.Blur(sigma_x: float = 0.0, sigma_y: float = 0.0, tile_mode: BlurTileMode = BlurTileMode.CLAMP)
```

| Field | Description |
| --- | --- |
| `sigma_x` | Horizontal Gaussian sigma (logical pixels). |
| `sigma_y` | Vertical Gaussian sigma (logical pixels). |
| `tile_mode` | Accepted for Flet parity; sampling currently clamps. |

`Container(blur=…)` also accepts a bare number or `(sigma_x, sigma_y)`.
