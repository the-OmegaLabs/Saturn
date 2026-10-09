# BlurTileMode

Edge sampling mode for `Blur`.

[← API index](./README.md)

Source: [`saturn/types.py`](../../saturn/types.py).

## Members

| Name | Value | Status |
| --- | --- | --- |
| `CLAMP` | `clamp` | Implemented (edge samples clamp) |

Only `CLAMP` is implemented for software and OpenGL. Saturn does not expose
unimplemented Flet names (`mirror` / `repeated` / `decal`) on this enum —
passing those strings (or any non-`CLAMP` value) to `Blur` /
`Container(blur=…)` raises `ValueError`.
