# Expressive controls and rendering

## Controls

- `MaterialExpressiveTheme`: light on-container colors; dark colors follow `page.theme_mode`.
- `ExpressiveButton` / `ExpressiveIconButton`: five size levels and shape changes when pressed or selected.
- `ToggleButton`, `ElevatedToggleButton`, `FilledTonalToggleButton`, and `OutlinedToggleButton`.
- `SplitButton`: separate primary and secondary actions; each ripple is clipped to its own asymmetric rounded shape.
- `ButtonGroup`: a pressed item grows by 15% while adjacent items shrink; drawing and hit testing use the same animated layout.
- `FloatingActionButton` and Small, Medium, Large, and Extended variants: the shape mask is softened in two Gaussian passes to create a shadow.
- `ListItem`: one to three lines of content, leading and trailing slots, and selected and disabled states.
- `LoadingIndicator`: a seven-shape RoundedPolygon morph from SoftBurst to Cookie9Sided, Pentagon, Pill, Sunny, Cookie4Sided, and Oval. Each segment lasts 650 ms while the indicator rotates continuously. Numeric `value` morphs Circle to SoftBurst; `contained=True` adds a container.
- `WavyProgressIndicator`, `LinearWavyProgressIndicator`, and `CircularWavyProgressIndicator`: determinate and indeterminate progress, moving waves, color, amplitude, wavelength, and speed.
- `FloatingToolbar` and Horizontal and Vertical variants: a 64 dp capsule that can collapse its leading and trailing slots. Hidden portions cannot be clicked.
- `FloatingActionButtonMenu` / `FloatingActionButtonMenuItem`: anchored menu with long-list scrolling and selection callbacks. Click outside or press Escape to close it.

## Example

```python
import saturn

def main(page):
    page.theme_mode = saturn.ThemeMode.DARK
    page.theme = saturn.Compose.Theme()
    page.add(
        saturn.Compose.LoadingIndicator(contained=True),
        saturn.Compose.WavyProgressIndicator(.6),
        saturn.Compose.FloatingToolbar(saturn.IconButton(saturn.Icons.EDIT), saturn.IconButton(saturn.Icons.SHARE)),
        saturn.Compose.FloatingActionButtonMenu([
            saturn.Compose.FloatingActionButtonMenuItem("Create", icon=saturn.Icons.ADD,
                                           on_click=lambda e: print("create")),
        ]),
    )

saturn.run(main)
```

- Basic showcase: `uv run python examples/expressive_demo.py`.
- Motion showcase: `uv run python examples/expressive_motion_demo.py`; add `--menu` or `--pressed` to inspect interaction states.
- Regression checks: `uv run python -m tests.expressive_checks`.
- Transition performance replay: `uv run python -m tests.floating_perf software` or `opengl`. These report the first-frame and cached-frame costs, excluding display synchronization waits.

## Rendering and resources

All new shapes are generated in a shared drawing path, so software, OpenGL, and Vulkan use the same outlines.
Outline morphs use pregenerated matching Bézier control points; no JVM is needed at runtime. `tools/ExportLoadingShapes.java` regenerates the JSON when the matching JetBrains Compose Material 3 desktop, AndroidX Graphics Shapes desktop, and their JVM dependencies are on the classpath. The source archives are not stored in this repository.
The generated loading-shape geometry in `saturn/_gen/loading_shapes.json` derives from AndroidX Compose Material 3 and Graphics Shapes. See the [attribution, exact versions, and source details](../saturn/_gen/NOTICE.md) and [Apache License 2.0 text](../saturn/_gen/LICENSE-APACHE-2.0.txt).

The text field notch uses segmented strokes without covering its parent background. For an empty field, the notch width and depth follow the label's floating progress. For a field with a value, the label and notch remain floated when focus changes.
Shadows are blurred and cached from the full shape, so a long label does not change the shadow's rounded structure.
Softening is computed on a low-resolution intermediate image that the GPU scales up. The software path separately caches the scaled result to avoid a full high-resolution blur on every expansion or collapse frame.
Control shape transitions still use the framework's interpolated animation; LoadingIndicator uses a damped spring response.
Connected ButtonGroup currently uses a 2 dp gap and has no overflow menu.
