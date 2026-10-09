# Saturn `examples/demo.py` — C++ parity inventory

Source: `examples/demo.py` + `examples/demo_common.py` (main @ `a80c62c`).
Theme: `ThemeMode.DARK`, baseline M3 (no indigo seed). Window: **960×800** (`DEMO_WIDTH`/`DEMO_HEIGHT`).

Golden PNG (this box): `/workspace/Saturn/.static/shots/demo-opengl-960x800.png`  
(OpenGL via Mesa llvmpipe / `LIBGL_ALWAYS_SOFTWARE=1`; see capture notes below.)

---

## Page / window

| Property | Value |
|---|---|
| `page.window.width/height` | 960 / 800 |
| `page.title` | `"saturn demo"` |
| `page.theme_mode` | `ThemeMode.DARK` |
| `page.bgcolor` | `Colors.SURFACE` → **#141218** |
| `page.padding` | **24** |
| `page.spacing` | **16** |

Root tree: `Column`-like page children with spacing 16 (via `page.add` / page spacing).

---

## Layout structure (top → bottom)

```
Page (pad 24, spacing 16, bg SURFACE)
├── brand_header Row (spacing 12, CrossAxisAlignment.CENTER)
│   ├── Image(logo 52×40, BoxFit.CONTAIN, color=PRIMARY)
│   ├── Text("Saturn Demo", size=28, weight=W_500, ON_SURFACE)
│   └── Text("v{version}", size=12, ON_SURFACE_VARIANT)
├── Text status line (size=13, ON_SURFACE_VARIANT)  // "interact with the controls below"
└── Row (spacing 24)
    ├── demo_panel "Controls" (width 440)
    │   └── Column (spacing 16, tight=True)
    │       ├── Text panel title size=18 W_500 ON_SURFACE
    │       ├── Row spacing=8: Button / FilledButton / OutlinedButton / IconButton
    │       ├── Row spacing=12 CENTER: TextField + Checkbox
    │       ├── Row spacing=12: Slider + Switch + ProgressRing
    │       ├── Row spacing=12: Dropdown + Image
    │       └── Row spacing=8: Dialog Button + SnackBar Button
    └── demo_panel "Scrollable list" (width 440)
        └── ListView 400×260, spacing=4, 30 items
```

### `demo_panel` chrome (`demo_common.py`)

- `Container(width=440, padding=20, bgcolor=SURFACE_CONTAINER_LOW, border_radius=16)`
- Inner `Column(spacing=16, tight=True)` with title `Text(size=18, weight=W_500, ON_SURFACE)`

### `brand_header`

- Logo: `.static/saturn-logo-transparent.png`, 52×40, tinted `PRIMARY`
- Title 28 / W_500; detail 12 / ON_SURFACE_VARIANT; row spacing 12

---

## Controls used (exact demo set)

| Control | Demo args / notes | Theme / metrics defaults (framework) |
|---|---|---|
| **Text** | status 13; list items 13; panel titles 18 W_500; header 28 W_500 / 12 | default size **14** if unspecified |
| **Image** | logo + `examples/assets/test_img.png` 140×70, `border_radius=8` | |
| **Button** (“Elevated”) | label `"Elevated"`, `icon=Icons.ADD` | elevated surface: bg `SURFACE_CONTAINER_LOW`, fg `PRIMARY`, elevation 1; height **40**, h-pad **24**, label **14**/500, icon **18**, gap 8, radius = height/2 (pill) |
| **FilledButton** | `"Filled"` | bg `PRIMARY`, fg `ON_PRIMARY`; same metrics |
| **OutlinedButton** | `"Outlined"` | bg none, fg `ON_SURFACE_VARIANT`, border `OUTLINE_VARIANT` |
| **IconButton** | `Icons.FAVORITE` | default side **40**, icon_size **24** (non-expressive) |
| **TextField** | `label="Name"` | text_size **16**, field h **56**, pad **16**, radius **4**, fill `SURFACE_CONTAINER_HIGHEST` |
| **Checkbox** | `"agree"` | box **18×18**, radius 2, active `PRIMARY` |
| **Slider** | min0 max100 divisions10 | intrinsic ~300×**48**; active `PRIMARY` |
| **Switch** | (no label) | track width **52**, height **40** |
| **ProgressRing** | value **0.6** | default size **40×40**, stroke_width **4**, color `PRIMARY` |
| **Dropdown** | hint `"dropdown..."`, options Alpha/Beta/Gamma, width **180** | text_size **16** |
| **Option** | keys a/b/g | |
| **ListView** | 30× `Container(Text, padding=8, border_radius=6, alternating SURFACE_CONTAINER_LOW / SURFACE_CONTAINER)`, spacing **4**, **400×260** | |
| **Container** | panels + list rows | |
| **Row / Column** | as above | Row/Column default spacing **10** if unspecified (demo always sets) |
| **AlertDialog** | title/content/actions Cancel(TextButton)+Delete(FilledButton) | title/content/actions pad **24**, inset **40** |
| **SnackBar** | `"Saved!"`, action `"Undo"`, duration **3000** | padding **24** |
| **TextButton** | dialog Cancel only | fg `PRIMARY`, no fill |

Icons: `Icons.ADD`, `Icons.FAVORITE` (material outlined/filled via saturn-icons).

---

## Dark theme colors (baseline M3 — what demo resolves)

| Token | Hex |
|---|---|
| SURFACE | `#141218` |
| ON_SURFACE | `#E6E0E9` |
| ON_SURFACE_VARIANT | `#CAC4D0` |
| PRIMARY | `#D0BCFF` |
| ON_PRIMARY | `#381E72` |
| PRIMARY_CONTAINER | `#4F378B` |
| SURFACE_CONTAINER_LOWEST | `#0F0D13` |
| SURFACE_CONTAINER_LOW | `#1D1B20` |
| SURFACE_CONTAINER | `#211F26` |
| SURFACE_CONTAINER_HIGH | `#2B2930` |
| SURFACE_CONTAINER_HIGHEST | `#36343B` |
| OUTLINE | `#938F99` |
| OUTLINE_VARIANT | `#49454F` |
| ERROR | `#F2B8B5` |
| SECONDARY_CONTAINER | `#4A4458` |
| ON_SECONDARY_CONTAINER | `#E8DEF8` |

List row alternating: odd `SURFACE_CONTAINER_LOW` (#1D1B20), even `SURFACE_CONTAINER` (#211F26).

---

## Typography / spacing / radii cheat sheet

**Sizes:** 12 (version), 13 (status + list items), 14 (button labels default), 16 (TextField/Dropdown), 18 (panel titles), 28 (page title).  
**Weights:** W_500 on titles / button labels (500).  
**Spacing:** page 16; panel column 16; header row 12; control rows 8 or 12; main two-column row 24; list spacing 4.  
**Padding:** page 24; panel 20; list item Container 8.  
**Radii:** panel 16; list item 6; demo Image 8; buttons pill (h/2≈20); TextField 4; Checkbox box 2.

---

## Capture notes (box)

```bash
# Need libGL.so symlink (distro only ships libGL.so.1):
mkdir -p /workspace/Saturn/.local-lib
ln -sfn /usr/lib/x86_64-linux-gnu/libGL.so.1 /workspace/Saturn/.local-lib/libGL.so

cd /workspace/Saturn/examples
LD_LIBRARY_PATH=/workspace/Saturn/.local-lib LIBGL_ALWAYS_SOFTWARE=1 \
  SDL_VIDEODRIVER=x11 DISPLAY=:4 \
  ../.venv/bin/python -c '... App(demo)+screenshot ...'
# Or: SATURN_SHOT=path SATURN_AUTOCLOSE=4 ... examples/demo.py --backend opengl
```

- **OpenGL worked** after `libGL.so` symlink + `LIBGL_ALWAYS_SOFTWARE=1` (Mesa); `renderer_name=opengl`, class `GLRenderer`, no fallback.
- Without symlink: falls back to software (`libGL.so` missing).
- Size saved: **960×800**. Existing `.static/shots/demo.png` is 944×761 (older client crop).
- Software fallback PNG also at `/workspace/demo-software-960x800.png` (pixels differ slightly from GL).
