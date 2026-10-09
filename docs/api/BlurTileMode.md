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

Only `CLAMP` is implemented for software and OpenGL. Passing `MIRROR`,
`REPEATED`, or `DECAL` to `Blur` / `Container(blur=…)` raises `ValueError`.
