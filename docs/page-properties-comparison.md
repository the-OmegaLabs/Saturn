# Page differences worth fixing

Checked on **2026-09-27** against installed **Flet 1.0.1** and Saturn's implementation at **b37c4a2**. Priorities below are recommendations for Saturn desktop applications. This document records findings and proposed fixes; implementation is still pending.

## Fix first

These issues can break ordinary application code or leave a configured property ineffective.

| Priority | Property / operation | Current Saturn problem | User impact | Simple repair |
| --- | --- | --- | --- | --- |
| P1 | `on_keyboard_event`, `on_resize` | Require lists. Assigning one callback fails during dispatch; handlers receive Page rather than an event | Common callback syntax fails. Keyboard handlers cannot read the key or modifiers, blocking useful shortcuts | Accept one callback or a handler list. Pass small keyboard and resize event objects; provide Page through `event.page` |
| P1 | `controls`, `overlay` followed by `update()` | Direct replacement or append does not attach new controls to Page | A control can draw while its events or later updates do not work | Reconcile changed top-level lists during `update()`. Preserve existing objects and attach only additions; clear obsolete focus/hover references on removal |
| P1 | `padding` | Layout treats padding as one number | Per-edge Padding values raise `TypeError`; asymmetric page layouts cannot use the normal API | Normalize numeric, Padding, and `None` values once, then use left/top/right/bottom independently |
| P1 | `theme`, `dark_theme`, `theme_mode` | `dark_theme` is stored but never selected | Switching to dark mode cannot use the configured dark theme | Resolve one effective theme from the current mode, apply its font/colors, and invalidate affected layout/drawing |
| P2 | `fonts` | Assigning a dictionary registers aliases; mutating it in place does not. The setter does not request a redraw | `page.fonts["Custom"] = path` can silently leave the old font active | Compare the small alias map during `update()` and register changed entries. Invalidate affected text caches and redraw |
| P2 | `title`, `window.title` | Page starts with an empty title, separate from App's startup title. Setting Window title does not update Page title | Reading and changing the title through different paths produces inconsistent state | Use one App-owned title; make both access paths read and write it |
| P2 | `window.maximized`, `minimized`, `full_screen` | Getters return requested cached flags, without synchronizing user actions | Application state can disagree with the actual window after title-bar actions | Read native state or update the cache from SDL window events |
| P2 | `disabled` | Root pointer hit tests check it, but overlay dispatch and keyboard forwarding to an already focused control can bypass it | Input may continue while the application expects the page to be disabled | Define the scope of Page disabling, then apply that rule consistently before pointer and keyboard dispatch |
| P2 | `services` | The Page list is unused; registering a FilePicker there does not assign its `page` | File dialogs may still work, but their result event's `page` remains `None` | Associate existing registered services with Page during `update()` through a small registration hook. No new service framework is needed for this fix |

### What currently fails

```python
# Common Flet callback syntax: current Saturn fails at dispatch.
page.on_keyboard_event = lambda event: print(event.key, event.ctrl)

# Current Saturn: drawing uses scalar padding arithmetic and raises TypeError.
page.padding = saturn.Padding.only(left=24, right=12)

# Current Saturn: update() does not attach this newly added control.
page.controls.append(saturn.Button("Save", on_click=save))
page.update()
```

These examples describe current problems, not the proposed API after repair.

### Current workarounds

```python
page.on_resize.append(lambda current_page: print(current_page.width))
page.padding = 10
page.add(saturn.Button("Save", on_click=save))
page.fonts = {**page.fonts, "Custom": "assets/Custom.ttf"}
page.title = "My application"
page.update()
```

There is currently no equivalent Page keyboard callback workaround that provides the key and modifier payload. `dark_theme` also has no automatic selection path; applications must select and assign their effective `theme` themselves.

## Useful missing desktop capabilities

Implement these when an application needs them. Each needs actual native behavior; accepting and storing a Python attribute is insufficient.

| Properties | Why they matter | Suggested scope |
| --- | --- | --- |
| `window.resizable`, `min_width`, `min_height`, `max_width`, `max_height` | Prevent resizing fixed-layout dialogs or shrinking content below a usable size | Connect to native resize capabilities and bounds; keep logical/device dimensions consistent |
| `window.left`, `window.top` | Position launchers, tool windows, and restore saved window locations | Expose native position and keep restored windows within available monitor bounds |
| `window.always_on_top` | Keep small utility windows accessible | One native topmost setting with live readback |
| `window.on_event`, `window.prevent_close` | Save state, warn about unsaved edits, or intercept closing | Add a small native event payload and a close-cancellation path. Flet `page.on_close` describes session expiration, so it is not the model for native closing |
| `platform_brightness`, `on_platform_brightness_change` | Keep SYSTEM theme in step with OS light/dark changes | Detect preference changes and reapply the effective theme when mode is SYSTEM |
| `media.device_pixel_ratio` or a documented native density accessor | Size custom drawing and images correctly on different displays | Expose the renderer/App's actual measured density first; add other media metrics only when supported |

`window.frameless` and transparency can help custom launchers, but require decisions about native composition, resizing, hit testing, and backend support. Handle them as a separate feature when needed.

## Clarify APIs that currently suggest unsupported behavior

| Property group | Finding | Recommended action |
| --- | --- | --- |
| Root `rotate`, `scale`, `offset`, positioning, and `animate_*` | Inherited fields exist, but Page root geometry/animations are not driven like child controls | Document or reject inactive root settings. Apply supported effects to a child Container/Stack instead of expanding root animation machinery solely for parity |
| Root `visible` and `opacity` | Affect the main control tree; background clearing and overlays happen separately | Document the scope and verify it before promising whole-window hiding or fading |

## Keep existing useful Saturn behavior

- `page.width` and `page.height` are read-only client dimensions. Native dimensions belong to `page.window.width` and `page.window.height`; no change is needed just to make assignment succeed.
- `page.renderer.anti_aliasing`, `.vsync`, and `.context` are useful native rendering APIs. Keep them as Saturn extensions. See [Renderer settings](./rendering.md).
- For scrollable page content, use the existing `ListView`. Root `scroll` and `auto_scroll` can remain optional until there is a concrete use case.

## Suggested implementation order and acceptance checks

1. **Events:** callback assignment works; key/modifier and resize dimensions are available; existing registration patterns have a deliberate migration path.
2. **Attachment:** direct child addition followed by `update()` supports both drawing and events; removing a focused child does not leave stale input targets.
3. **Padding:** numeric and asymmetric padding produce correct content bounds without exceptions.
4. **Themes, fonts, and services:** light/dark selection changes the effective font/colors; alias changes are reflected after `update()`; FilePicker result events resolve to their owning Page.
5. **Window state:** titles agree across access paths; user minimize/maximize actions are reflected; native limits and close handling work when added.
6. **Input scope and inactive fields:** disabled input follows a documented policy; unsupported root settings are clear.

Small source-based or event tests are sufficient for registration and state plumbing. Native window properties need actual window checks. Padding/theme/font changes need rendered verification on the affected backends. These gates are proposed, not results of new implementation work.

## Evidence

Findings are based on the previous source audit and focused stub probes, rather than a full Flet frontend equivalence test:

- [Page](../saturn/page.py): property setters, list registration, dispatch, root layout, and input forwarding.
- [Control](../saturn/control.py) and [event dispatch](../saturn/event.py): attachment, rendering effects, and event ownership.
- [App](../saturn/app.py): native lifecycle, resize, density, and queued window operations.
- [Font registration](../saturn/text.py): alias registration and font lookup.
- [Services](../saturn/services.py): FilePicker ownership and result event Page lookup. Flet uses contextual service registration through a private registry; its `Page.services` list is not itself the registration API.
- Installed Flet source: `controls/page.py`, `controls/base_page.py`, `controls/core/window.py`, and `controls/services/service.py` under `.venv/Lib/site-packages/flet/`.

Browser/session properties such as client IP, user agent, URL, PWA, WebAssembly, OAuth, and transport connection state do not solve current native Page issues. They are outside this repair list. Views/routes, navigation slots, and accessibility remain separate feature work.

[Documentation home](./README.md) · [Startup comparison](./run-comparison.md)
