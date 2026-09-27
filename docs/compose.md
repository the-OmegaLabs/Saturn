# Compose namespace and Flet API verification

## Implemented grouping

Material 3 Expressive controls are available through `saturn.Compose`. Standard controls remain available as `saturn.Text`, `saturn.Button`, `saturn.ListView`, and other top-level names. Existing top-level Expressive names remain available for migration. Compose button variants reuse the drawing implementation and enable Expressive sizing and shape animation by default; standard top-level buttons keep their existing defaults.

```python
import saturn


def main(page: saturn.Page):
    page.theme = saturn.Compose.Theme()
    page.add(
        saturn.Text("Standard control"),
        saturn.Compose.Button("Expressive"),
        saturn.Compose.LoadingIndicator(),
    )


saturn.run(main, backend=saturn.Renderer.OPENGL)
```

| Namespace | Main members | Purpose |
| --- | --- | --- |
| `saturn` | `Button`, `IconButton`, `Text`, `TextField`, `ListView`, `FloatingActionButton`, and others | Standard interfaces; behavior is limited to Saturn's implemented subset |
| `saturn.Compose` | `Theme`, `Button`, `IconButton`, Filled/Tonal/Elevated/Outlined/Text buttons, `SplitButton`, `ButtonGroup`, Toggle variants, FAB size variants, `ListItem`, Loading/Wavy variants, FloatingToolbar, and FAB Menu variants | Saturn's Material 3 Expressive extensions |

`Compose.Button` aliases `ExpressiveButton`, `Compose.IconButton` aliases `ExpressiveIconButton`, and `Compose.Theme` aliases `MaterialExpressiveTheme`. `Compose.FilledButton`, `FilledTonalButton`, `ElevatedButton`, `OutlinedButton`, and `TextButton` default to `size="small"`, enabling Expressive behavior. `Compose.FloatingActionButton` shares its implementation with the top-level class.

## Verification against the installed Flet package

On 2026-09-23, **Flet 1.0.1** was installed and imported in the project virtual environment. The repository's `flet-skill/` API reference and the actual package exports and constructor signatures were compared with `saturn.__all__`. There were **68 shared class names**. `python -m tests.flet_api_checks` constructed **29 common controls** in both packages, compared stored shared parameters, and exercised Saturn text, input, Slider, and FAB behavior. These checks cover the tested interfaces and paths; they do not establish identical Flutter rendering or support for every Flet parameter.

| Controls constructed in both packages | Result |
| --- | --- |
| `Text`, `Button`, `TextField`, `ListView`, `Row`, `Column`, `Container` | Tested shared parameters passed; Saturn normalizes `Container.padding=8` to four sides of 8 |
| `Checkbox`, `Switch`, `Slider`, `Dropdown`, `Radio`, `ProgressBar`, `FloatingActionButton` | Tested shared parameters passed; FAB used each package's own `Icons.ADD` |
| `Card`, `Divider`, Filled/Tonal/Outlined/Text buttons, `Icon`, `IconButton`, `Image`, `ProgressRing`, `Stack`, `Tooltip`, `AlertDialog`, `GestureDetector`, `DropdownOption` | Tested shared parameters passed |

Behavior checks found and fixed issues that constructor inspection missed:

- `Text(no_wrap=True)` previously produced no drawing lines. It now preserves hard line breaks and clips only when needed.
- `Slider(min != 0, divisions=...)` previously quantized around zero. It now quantizes relative to `min`.
- `TextField` now implements `max_length`, `shift_enter`, `show_cursor`, and `obscuring_character` input or display behavior. `show_cursor=False` hides the caret and stops its blink timer; `max_length=-1` means no limit.
- Standard `FloatingActionButton` now supports `mini`, text `content`, and `foreground_color`.

The script exercises these paths. Signature comparisons also expose unsupported areas. Flet 1.0.1 `ListView` includes `reverse`, `build_controls_on_demand`, and `cache_extent`, which Saturn has not implemented. `TextField.keyboard_type` and other input behaviors have not been verified. Some Saturn `**base` arguments accept unsupported parameters, so successful construction does not prove that a parameter works. The script prints counts and examples of parameters without explicit implementations for each control.

| Interface | Flet 1.0.1 findings | Saturn status and follow-up |
| --- | --- | --- |
| `Button`, `Text`, `Row`, `Column`, `Container` | Shared class names exist | Common constructor and interaction subset; verify actual rendering rather than counting accepted but ignored parameters |
| `ListView` | Includes `item_extent`, `reverse`, `build_controls_on_demand`, and others | Fixed extent layout and visible-row placement are implemented; `reverse` and other parameters need further checks |
| `FloatingActionButton` | Includes `mini`, `shape`, and others | `mini`, text `content`, and `foreground_color` are supported; `shape` and some visual parameters are not. Expressive size variants live in Compose |
| `TextField` | Includes `keyboard_type` and others | Constructor coverage is incomplete; check input semantics parameter by parameter |
| `ElevatedButton`, `ListItem`, `LoadingIndicator`, `SplitButton`, `ButtonGroup` | No such top-level names | Saturn extensions grouped in Compose; old top-level aliases remain for migration |
| `MaterialExpressiveTheme` | No such top-level name | `Compose.Theme` is a Saturn extension |

**Interface limits:** Saturn does not implement the full Flet 1.0.1 API. `Control.**_ignored` and some controls' `**base` accept arguments without corresponding effects. Follow-up work should implement commonly used properties and document or explicitly report unsupported ones.

## Migration and follow-up

1. Use `saturn.Compose.*` for new Expressive components; replace older top-level Expressive names gradually.
2. Applications requiring matching Flet behavior must verify the parameters and events they actually use. Current checks cover common construction and selected behaviors.
3. Removing old top-level Expressive aliases in a future breaking release needs a separate migration plan. Existing imports remain supported in this version.

Third-party origins and licensing for Expressive loading graphics are recorded in [NOTICE](../saturn/_gen/NOTICE.md) and the [Apache 2.0 license](../saturn/_gen/LICENSE-APACHE-2.0.txt).
