# Built-in effects and user GLSL

`Shader` paints a rectangle directly on the GPU with OpenGL or Vulkan. Use
the same `shader` parameter for a built-in effect, a GLSL string, or a
`pathlib.Path` containing GLSL. Ordinary controls can be layered over it with
`Stack`. It does not filter another control or sample the desktop behind it.

## Built-in effects

```python
background = saturn.Shader(
    shader=saturn.ShaderEffect.PLASMA,
    color="#392554", secondary_color="#C8A9FF",
    uniforms={"intensity": 1.0, "frequency": 4.0},
    speed=0.8, border_radius=24, height=240,
)
page.add(background)
```

`GRADIENT`, `NOISE`, `RIPPLE`, and `PLASMA` are available, as are their
lowercase strings. The older positional/keyword `effect` remains an alias;
pass either `effect` or `shader` at construction, not both.

| Built-in uniform | Default | Meaning |
| --- | --- | --- |
| `intensity` | `1.0` | `0..1`, blend between a static gradient and the effect |
| `frequency` | `4.0` | Positive detail/ring density; unused by Gradient |
| `center` | `(0.5, 0.5)` | Two normalized coordinates in `0..1` |
| `angle` | `0.0` | Gradient orientation in radians |

Unsupported built-in uniform names and invalid numeric values raise an error.

## Write GLSL

The portable entry point returns **straight-alpha RGBA** from normalized,
top-left UV coordinates:

```python
glsl = """
uniform float frequency;
uniform vec3 tint;
vec4 mainImage(vec2 uv) {
    float wave = sin(uv.x * frequency + u_time) * 0.5 + 0.5;
    return vec4(tint * wave, 1.0);
}
"""
effect = saturn.Shader(shader=glsl,
                       uniforms={"frequency": 12.0, "tint": (0.4, 0.8, 1.0)},
                       height=260, border_radius=24)
page.add(effect)
```

Saturn supplies the native `main()` and GLSL version for each backend. A
Shadertoy-style `void mainImage(out vec4 color, in vec2 pixel)` entry point
also works; its pixel coordinates are top-left **logical** pixels. This does
not supply Shadertoy textures, mouse input or multipass buffers.

| Supplied value | Type | Meaning |
| --- | --- | --- |
| `u_resolution` | `vec2` | Local Shader width/height in logical pixels |
| `u_time` | `float` | Time offset plus elapsed time multiplied by speed |
| `u_color`, `u_secondary_color` | `vec4` | Shader colors in normalized RGBA |
| `u_border_radius` | `float` | Local rounded-mask radius |
| `u_opacity` | `float` | Inherited control opacity; applied by Saturn's output wrapper |
| `iTime`, `iResolution` | `float`, `vec3` | Aliases for time and `(width, height, 1)` |

Do not redeclare supplied uniforms. Declare custom `float`, `int`, `bool` or
`vec2`/`vec3`/`vec4` uniforms and pass matching Python values. Undeclared dict
entries generate declarations: numeric values become float, bool becomes
bool, and tuples/lists of length 2–4 become vectors. Declared uniforms omitted
from the dict default to zero/false. At most 252 custom uniforms are supported.
Arrays, matrices and arbitrary sampler uniforms are not exposed. An optional
`ShaderBuffer` supports instanced vertex/fragment programs and one sampled GPU buffer.

## Includes and source files

```python
from pathlib import Path

# File includes resolve relative to their containing file.
effect = saturn.Shader(shader=Path("effects/orb.glsl"), uniforms=params)

# A source string can use explicit include folders or a snippet map.
glsl = '#include "noise.glsl"\nvec4 mainImage(vec2 uv) { return vec4(noise(uv)); }'
effect = saturn.Shader(shader=glsl, include_dirs=["effects"])
effect = saturn.Shader(shader=glsl, includes={"noise.glsl": noise_source})
```

Missing includes and cycles are reported. Source files and includes are read
once until `effect.reload()` is called. Assign new source through
`effect.shader = glsl` and call `effect.update()` to change programs.

## Animation, updates and errors

```python
effect.uniforms["frequency"] = 8.0
effect.update()
effect.animate = False
effect.update()
effect.on_error = lambda e: print(e.data)
```

`animate=True` and nonzero `speed` request frames while visible on GPU
backends. `animate=False` holds the last elapsed value; `time` is an offset.
The clock is elapsed wall time since construction, so resuming can advance
past a pause. Hidden ancestors and Software fallback do not request fragment
animation. The defaults are speed 1, time 0, radius 0, and intrinsic size up
to 240 × 160 when no explicit dimensions are supplied.

Programs are cached by expanded source and uniform layout; changing uniform
values does not recompile. OpenGL compiles through its driver. Vulkan uses
glslang to compile SPIR-V on the first draw and caches successful bytecode
in memory. Install the Vulkan SDK compiler on PATH or set its executable:

```powershell
$env:SATURN_GLSLANG = 'C:\VulkanSDK\<version>\Bin\glslangValidator.exe'
python examples/orb_glsl.py --backend vulkan --screen editor
```

Built-in Vulkan effects use packaged SPIR-V and need no external compiler.
First compilation is synchronous on the UI thread and can pause a frame.
Compilation failures draw `fallback_color` (or `color`), set `effect.error`,
and dispatch `on_error` once per changed error message. Fix the source and
update/reload to recover. Software always draws a static fallback color.

The usual clipping, transforms, opacity, drawing order and AA apply. The
rounded output mask uses derivatives. GPU rotated scissor bounds remain
axis aligned. Each custom fragment needs its own draw; ordinary controls and
built-in effects keep their existing batching. Vulkan custom uniform uploads
are capped at 1 MiB per frame.

## Optional GPU buffer

```python
particles = saturn.ShaderBuffer(
    vertex_shader=Path("effects/particles.vert"),
    fragment_shader=Path("effects/particles.frag"),
    instances=384 * 96 * 6,
)
effect = saturn.Shader(shader=Path("effects/composite.glsl"),
                       buffer=particles, uniforms=params)
```

Each buffer stage defines `void main()` and shares the final fragment's custom
uniform layout and time/resolution uniforms. Use `SATURN_LOCATION(n)` on
varyings, `SATURN_VERTEX_ID` and `SATURN_INSTANCE_ID` in the vertex stage.
Each instance draws six triangle vertices. Output coordinates are native clip
coordinates; `SATURN_VULKAN` is defined for Vulkan, whose viewport Y points down.
The buffer uses RGBA8, additive RGB blending (`ONE, ONE`) and accumulated alpha
(`ONE, ONE_MINUS_SRC_ALPHA`). Return premultiplied RGBA from the buffer fragment.
Instances must be an integer from 1 to 1,000,000.

The final `mainImage` samples it with `saturnSampleBuffer(uv)`, using top-left
UV coordinates on both backends, and returns straight RGBA. This helper requires
a buffer. Inherited opacity, clipping and transforms apply to the final composite.
The offscreen target tracks local dimensions, pixel ratio and antialiasing scale;
it is reused until dimensions change. Programs and inactive targets have bounded
caches and are released with the renderer. Buffer images stay on the GPU.
Software renders the same static fallback as a Shader without a buffer.
This is one optional pass; it does not provide a general render graph or access
to other controls' frame contents.

## Orb GLSL adaptation

[orb_glsl.py](../examples/orb_glsl.py) provides all 13 Orb presets with an
independent native settings window. [orb_gallery.py](../examples/orb_gallery.py)
shows the complete catalog together. Includes, preset defaults and stages live
in [.static/shaders](../.static/shaders). The upstream typed Metal export of
`effect.wgsl` is converted to GLSL by `tools/port_orb_shaders.py`.
Particle Ribbons uses instanced GPU geometry, an additive offscreen target and
the original glass/channel-refraction composite. Final output is converted
from premultiplied to straight alpha for Saturn. See [Orb presets](./orb.md)
for the catalog, settings and verification. Shader compiler and floating-point
differences can change pixels across backends; bit-identical output is not guaranteed.

Original project: [LerSent001/orb](https://github.com/LerSent001/orb).
Copyright (c) 2026 LerSent001. The complete [MIT license](../.static/shaders/ORB-LICENSE.txt)
and copyright notice are retained beside the adapted source and attributed in the repository README.
See [runnable demos](./effects-demos.md).
