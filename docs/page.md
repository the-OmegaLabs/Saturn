# Page

Page owns the control tree, overlays, application services, theme, and input events. Window changes belong to `page.window`; backend options belong to `page.renderer`.

```python
import saturn


def main(page: saturn.Page):
    page.title = "My application"
    page.window.width = 900
    page.window.height = 640
    page.padding = saturn.Padding.only(left=24, top=16, right=12, bottom=16)
    page.add(saturn.Text("Hello"))


saturn.run(main)
```

`page.width` and `page.height` report logical client dimensions and are read-only. `page.window.width` and `.height` configure outer window dimensions. `page.media.device_pixel_ratio` reports the measured device density; the other Flet media fields are not implemented.

## Fonts

Register aliases and use them on individual controls or in a theme:

```python
page.fonts = {
    "Body": "assets/Body.ttf",
    "Heading": "https://example.com/fonts/Heading.woff2",
}
page.theme = saturn.Theme(font_family="Body")
page.add(saturn.Text("Custom heading", font_family="Heading", size=28))

# In-place mutation takes effect on update().
page.fonts["Body"] = "assets/Replacement.otf"
page.update()
```

Local `.ttf`, `.otf`, `.ttc`, `.woff`, and `.woff2` fonts are supported. Relative paths resolve from the current working directory, then from `assets/`; use absolute paths for predictable packaged application behavior. Font collections use their default face.

HTTP(S) sources load in a background worker. Text uses fallback fonts until loading completes, then Saturn invalidates text measurements and rendered caches, recalculates layout, and requests a redraw. Compressed remote fonts are decoded into a local SFNT cache; URLs without a filename extension also work.

Downloads use a 20-second timeout and a 32 MiB limit. Failures emit a warning and retain fallback text. The cache lives under the system temporary directory in `saturn-font-cache/downloads`, keyed by the complete URL. Registering the same URL again reuses its cached file; use a new URL when the server's font content changes. Local font files are not watched for filesystem changes.

## Events

Assign one callback or a list. Callbacks can be synchronous or asynchronous and accept zero arguments or one event argument:

```python
def resized(event: saturn.PageResizeEvent):
    print(event.width, event.height, event.page.title)

async def keyboard(event: saturn.KeyboardEvent):
    if event.ctrl and event.key == "S":
        event.page.title = "Saved"

page.on_resize = resized
page.on_keyboard_event = keyboard

# Optional existing list registration style.
page.on_resize = [resized]
page.on_resize.append(lambda: print("Size changed"))
```

| Event | Payload |
| --- | --- |
| `on_resize` | `width`, `height` in logical pixels; `page` |
| `on_keyboard_event` | `key`, `shift`, `ctrl`, `alt`, `meta`; `page` |
| `on_platform_brightness_change` | `brightness` as `"light"` / `"dark"`; `page` |

**Migration:** earlier Saturn Page handlers received Page itself. They now receive the event, so change `current_page.width` to `event.width` or `event.page.width`. Handler lists remain supported.

Handlers run off the UI thread, using reusable workers for synchronous code and the application async loop for coroutines. A synchronous callback returning an awaitable is also awaited. Update controls and call `page.update()` to request layout/redraw. Obtain the owning Page through `event.page`; direct GPU/SDL operations belong to the UI thread. See [Renderer settings](./rendering.md) for renderer context access.

## Themes and platform preference

```python
page.theme = saturn.Theme(font_family="Body")
page.dark_theme = saturn.Theme(font_family="Body")
page.theme_mode = saturn.ThemeMode.SYSTEM
page.on_platform_brightness_change = lambda event: print(event.brightness)
```

LIGHT uses `theme`; DARK uses `dark_theme` when supplied, otherwise `theme`. SYSTEM selects the same way using `page.platform_brightness`. Windows application-theme changes are checked approximately once per second. Other platforms currently default to light preference detection; explicit LIGHT and DARK selections work everywhere.

Assigning a theme/mode or mutating a theme then calling `page.update()` applies the effective font and supported color palette. `Theme.color_scheme_seed` selects supported palettes; it is not a general dynamic Material color generator. Themes and font aliases currently belong to Saturn's active application context.

## Controls, overlays, and services

Direct changes to top-level and nested control lists are reconciled on `update()`:

```python
button = saturn.Button("Save", on_click=lambda event: print(event.page.title))
page.controls.append(button)
page.update()

page.controls.remove(button)
page.update()

picker = saturn.FilePicker(on_result=lambda event: print(event.page.title))
page.services.append(picker)
page.update()
```

Additions are attached to Page without reattaching unchanged trees. Removed subtrees lose their Page/parent and obsolete focus, press, hover, and animation references. Overlays use the same reconciliation; use `page.show_dialog(dialog)` and `page.pop_dialog()` for dialog lifecycle handling. Call `page.update()` after nested mutations, or call the owning control's `update()` to reconcile only its subtree. Leaf updates do not scan unrelated list rows.

Services are explicitly registered through `page.services`, including FilePicker. Adding/removing a service and calling `update()` sets/clears its Page ownership. This does not provide every Flet service or Flet's contextual automatic service registry.

## Input and visual scope

`page.disabled = True` followed by `page.update()` clears focus, press, and hover and blocks control/overlay pointer, keyboard, IME, and wheel input. Resize, platform-brightness, and native window events still operate. Re-enable input with `page.disabled = False` and `page.update()`.

Root `visible` and `opacity` affect the main control tree; background clearing and overlays are separate. The background uses `page.bgcolor`, then `page.window.bgcolor`, then the active theme surface. Use `page.window.visible` or `.opacity` for native whole-window behavior. Root positioning, rotation, scale, and `animate_*` are not Page geometry APIs. Child rotation, per-axis scale, offset, opacity, size and position animations are implemented. GPU rotated clips remain conservative axis-aligned rectangles. Put scrollable content in the existing `ListView`.

## Local navigation and effects

Use `child = page.open_subpage(main, title="Settings")` for an independent owned native window. It inherits Page controls/events and has its own `.window`, `.renderer`, focus and HWND. Operate it with `add()`, `update()`, `show()`, `hide()`, `close()` and `attach()`. Closing an owner closes its descendants; closing a child leaves the main window running. `page.route = value` and `page.go(value)` update one shared application route and dispatch `RouteChangeEvent` to every open Page with `on_route_change`. The handler chooses which windows or controls to show. Browser history and the earlier in-window View stack are not implemented.

Tab/Shift+Tab traverse enabled focusable controls. Nonblocking SnackBars do not trap focus; a visible AlertDialog restricts traversal to its own controls. `control.focus()` and `can_request_focus` support explicit focus choices.

See [Subpages](./subpages.md), [Shaders](./shaders.md) and the [runnable demos](./effects-demos.md).

## Verification

`python tests/page_compatibility_checks.py` passes for typed events, actual App async dispatch, top-level attachment/removal, FilePicker ownership, disabled input, themes, rendered font/padding changes, TTC/WOFF files, and real HTTP download/cache behavior. `python tests/flet_api_checks.py` verifies common APIs against installed Flet 1.0.1 and reports broader unsupported parameters.

[Native windows](./window.md) · [Renderer settings](./rendering.md) · [Remaining Page differences](./page-properties-comparison.md) · [Documentation home](./README.md)
