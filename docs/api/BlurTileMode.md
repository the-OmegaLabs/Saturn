# BlurTileMode

How samples outside the source bounds are treated during blur.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py).

## Members

| Name | Value |
| --- | --- |
| `CLAMP` | `clamp` |
| `MIRROR` | `mirror` |
| `REPEATED` | `repeated` |
| `DECAL` | `decal` |

Saturn currently clamps edge samples for both software and OpenGL paths.
