# BlurTileMode

Edge sampling mode for `Blur` (Flet name compatibility).

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py).

## Members

| Name | Value | Status |
| --- | --- | --- |
| `CLAMP` | `clamp` | Implemented (edge samples clamp) |
| `MIRROR` | `mirror` | Not implemented — `ValueError` |
| `REPEATED` | `repeated` | Not implemented — `ValueError` |
| `DECAL` | `decal` | Not implemented — `ValueError` |

Only `CLAMP` is implemented for software and OpenGL. The other members exist so
Flet-style names remain on the enum; passing them to `Blur` /
`Container(blur=…)` raises `ValueError`.
