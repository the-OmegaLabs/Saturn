# Flet Page and Saturn Page: property comparison

Checked on **2026-09-27** against the installed **Flet 1.0.1** Python package and Saturn revision **b37c4a2**. This is a property audit, with suggested alignment work. It does not change framework behavior.

## Scope and result

The inventory includes public dataclass fields, property descriptors, and inherited public state. Saturn's initialized instance attributes are included. Methods, private names, and Flet's constructor-only `sess` and `ref` arguments are excluded. Arbitrarily assigning a new Python attribute does not make it a supported property.

| Inventory | Count |
| --- | ---: |
| Flet Page public properties | 86 |
| Saturn Page public properties | 45 |
| Names present in both | 26 |
| Flet names absent from Saturn | 60 |
| Saturn names absent from Flet Page | 19 |

These are **name counts, not compatibility scores**. Some same-name Saturn fields are stored without effect. Most Saturn-only names come from its base Control and do not implement root-page layout or animation.

Inheritance differs:

```text
Flet:   Page -> BasePage -> AdaptiveControl -> Control -> BaseControl
Saturn: Page -> Control
```

Flet Page does not inherit LayoutControl. Do not assume every Flet widget transform is also a Flet Page property.

## Sources and verification

The installed package is the version-pinned reference. Source locations under `.venv/Lib/site-packages/flet/`:

| Source | Relevant declarations |
| --- | --- |
| `controls/page.py` | Page at line 484; fields at 492-713; visibility and session descriptors at 898 and 1304-1359 |
| `controls/base_page.py` | BasePage at line 136; views/theme/media/dimensions at 159-279; root-view property forwarding at 581-832 |
| `controls/core/view.py` | Root controls, alignment, spacing, padding, background, and services |
| `controls/control.py`, `controls/adaptive_control.py`, `controls/base_control.py` | Inherited fields and parent/page descriptors |
| `controls/core/window.py` | Native window fields at 127-335 |
| `controls/services/service.py` | Service initialization auto-registers through the current Page's private registry at 39-54 |

Saturn sources: [Page and Window](../saturn/page.py), [Control](../saturn/control.py), [application lifecycle](../saturn/app.py), [font registration](../saturn/text.py), and [event dispatch](../saturn/event.py).

The [official Flet Page reference](https://flet.dev/docs/controls/page/) is useful for navigation, but live documentation can change independently of the installed version. The counts and differences here come from local source and inspection.

Verification used `dataclasses.fields(flet.Page)`, property descriptors across both inheritance chains, and a Saturn Page constructed with a stub application. Focused probes checked read-only setters, event dispatch, padding arithmetic, direct child attachment, font dictionary registration, and initial title state. No Flet frontend, browser session, or visual equivalence test was run for this report.

## 1. Shared property names: all 26

`RW` means a setter or ordinary writable field exists. `RO` means a getter-only descriptor. Flet client-reported fields can be writable in Python even when their documented contract is read-only.

| Property | Flet 1.0.1 | Saturn | Difference / alignment action |
| --- | --- | --- | --- |
| `bgcolor` | RW root-view background; default `None` | RW; default `None`, clears to theme surface | Common purpose. Saturn clears the background separately from root visibility and opacity |
| `controls` | RW list delegated to the root View | RW plain list, initially `[]` | Direct replacement/append plus `update()` does not attach Saturn children. Use `add()`/`insert()` until attachment is reconciled |
| `dark_theme` | RW theme for dark mode; default `None` | RW field, default `None` | **Stored only:** never selected by Saturn's theme code |
| `data` | RW application metadata; default `None` | RW metadata; default `None` | Common purpose; not a rendering property |
| `disabled` | RW inherited Control flag; default `False` | RW inherited flag; default `False` | Saturn blocks main-tree pointer hit tests, but overlays and forwarding to an already focused control have exceptions |
| `expand` | RW inherited Control field; default `None` | RW inherited field; default `None` | Saturn Page has no parent flex allocation; its root layout uses the client viewport directly |
| `fonts` | RW alias map, default `None`; accepts font URLs or asset paths | RW alias map, default `{}`; setter copies and registers local paths | Saturn in-place dictionary mutation does not register a font. Assign a new dictionary; remote loading is not implemented |
| `height` | Client logical height; default `None`, documented RO | RO live client logical height | Both use `window.height` for changing native dimensions; Saturn rejects assignment immediately |
| `horizontal_alignment` | RW root-view alignment; default `START` | RW Column alignment; default `START` | Similar common layout purpose; enum classes and detailed layout implementation are package-specific |
| `on_keyboard_event` | One optional callback, default `None`; gets a KeyboardEvent | Handler list, default `[]`; each gets Page | **Incompatible registration and payload:** no key/modifier data is passed in Saturn |
| `on_resize` | One optional callback, default `None`; gets a PageResizeEvent | Handler list, default `[]`; each gets Page | **Incompatible registration and payload:** dimensions must be read from Saturn Page |
| `opacity` | RW inherited Control field; default `1.0` | RW inherited field; default `1.0` | Saturn applies opacity to the main tree; background clear and overlays are outside that effect stack |
| `overlay` | RO descriptor returning a mutable overlay list | RW plain list, initially `[]` | Flet permits list mutation but not replacing the descriptor. Saturn also needs attachment for added overlay controls; dialogs use `show_dialog()` |
| `padding` | RW PaddingValue; defaults to `Padding.all(10)` | RW numeric value; default `10` | **Partial:** Saturn performs scalar arithmetic and fails with per-edge Padding. Normalize it and use four edges in layout |
| `page` | RO owning-page lookup; Page itself resolves to itself | RW inherited field, root default `None` | Different root identity; Saturn should explicitly make the root own itself if this contract is wanted |
| `parent` | RO parent lookup; root `None` | RW inherited field; root `None` | Default matches; mutability differs |
| `services` | RW root-view service references; actual services auto-register through a separate Page registry | RW plain list, default `[]` | **Stored only:** Saturn never attaches or processes this Page list; Flet's list itself is not the registration API |
| `spacing` | RW root-view vertical spacing; default `10` | RW Column spacing; default `10` | Similar common purpose; placement is performed by Saturn's Column |
| `theme` | RW light theme; default `None` | RW theme; default `None` | Saturn uses a smaller implementation and changes module-global font/color state; it does not select `dark_theme` |
| `theme_mode` | RW; default `SYSTEM` | RW; default `SYSTEM` | Saturn reads the system preference on initialization/assignment; no Page brightness-change event or automatic recheck is wired |
| `title` | RW client page/native title state; default `None` | RW Page title, initially empty string | Can disagree with the App's startup title or `window.title`. Use a single source of truth |
| `tooltip` | RW inherited string or Tooltip; default `None` | RW inherited field; default `None` | Saturn root rect stays zero-sized, so a Page-level hover tooltip is not normally reachable |
| `vertical_alignment` | RW root-view alignment; default `START` | RW Column alignment; default `START` | Similar common layout purpose; verify individual alignment values if migrating |
| `visible` | RW inherited Control flag; default `True` | RW inherited flag; default `True` | Saturn hides the main control tree, while background clear and overlays still run |
| `width` | Client logical width; default `None`, documented RO | RO live client logical width | Set `window.width` instead; Saturn rejects Page assignment immediately |
| `window` | RW Flet Window object | RW Saturn Window object | Same access path, substantially different nested coverage; see section 4 |

### Concrete migration traps

```python
# Flet: one callback receiving an event.
page.on_resize = lambda event: print(event.width, event.height)
page.on_keyboard_event = lambda event: print(event.key, event.ctrl)

# Current Saturn: lists; handlers receive Page.
page.on_resize.append(lambda current_page: print(current_page.width, current_page.height))
page.on_keyboard_event.append(lambda current_page: print("Key down"))
# Current Saturn does not provide the key or modifiers to this handler.
```

Assigning a single callback to Saturn's event field succeeds as a Python assignment, then fails when `_dispatch()` tries `list(handlers)`. It is not compatible with Flet's callback property.

```python
# Current Saturn: reliable child and font registration.
page.add(saturn.Text("Hello"))
page.fonts = {**page.fonts, "MyFont": "assets/MyFont.ttf"}
page.update()
```

Changing ordinary stored layout properties generally needs `page.update()`. Saturn's theme setters already request an update. Its font setter registers aliases but does not itself request a redraw.

## 2. Flet properties absent from Saturn: all 60

Every name below is missing from Saturn's declared/initialized Page API. Python may still accept an assignment with that name; nothing then consumes it.

### Root structure, layout, and decoration: 19

| Property | Flet purpose | Suggested Saturn treatment |
| --- | --- | --- |
| `adaptive` | Inherited platform-adaptive behavior | Add only with real platform-specific control behavior |
| `appbar` | Root-view top app bar | Add a dedicated root layout slot if needed |
| `auto_scroll` | Root content follows its end | Implement together with root scrolling |
| `badge` | Inherited badge decoration | Implement an actual badge drawing path |
| `bottom_appbar` | Root-view bottom app bar | Reserve a bottom layout slot |
| `col` | Inherited ResponsiveRow column allocation | Useful for child controls; define whether it has any Page effect |
| `decoration` | Root-view background box decoration | Connect to a supported decoration drawing path |
| `drawer` | Start-side root drawer | Implement drawer layout, dismissal, and input behavior |
| `end_drawer` | End-side root drawer | Same requirements as `drawer` |
| `expand_loose` | Inherited loose expansion behavior | Define child-layout semantics before adding a field |
| `floating_action_button` | Root floating action button slot | Compose above content with explicit placement |
| `floating_action_button_location` | Floating button position | Pair with the root FAB slot |
| `foreground_decoration` | Decoration painted over root content | Implement drawing and input rules |
| `key` | Control identity key | Add a deliberate identity/diff contract if needed |
| `navigation_bar` | Root-view navigation bar | Add a layout slot and navigation behavior |
| `rtl` | Right-to-left direction | Support text direction and layout together |
| `scroll` | Root-view scrolling mode/scrollbar | Current workaround: place content inside the original `ListView` |
| `theme_animation_style` | Theme-transition animation settings | Implement actual theme interpolation before exposing settings |
| `views` | Page View stack | Optional navigation architecture; not needed for simple single-window UI |

### Environment, locale, and screenshots: 14

| Property | Flet purpose / contract | Suggested Saturn treatment |
| --- | --- | --- |
| `app_visible` | RO actual application/tab lifecycle visibility | Derive from native visibility and lifecycle events; separate from root `visible` |
| `client_ip` | Client-reported web address | No equivalent required for native-only UI |
| `client_user_agent` | Client-reported browser information | No equivalent required for native-only UI |
| `debug` | Client debug-build status, documented RO | Define meaningful local status if exposed |
| `enable_screenshots` | Enables client screenshot capture | Saturn captures locally without this permission switch; see its `take_screenshot()` |
| `locale_configuration` | Locale and localization configuration | Add translation, locale, and direction behavior together |
| `media` | Client media metrics including density, safe areas, and insets | Expose measured native density first; define supported metrics |
| `platform` | Host platform identity | Straightforward local platform mapping |
| `platform_brightness` | Client-reported system brightness, documented RO | Expose OS preference and implement updates |
| `pwa` | PWA mode, documented RO | Web-specific; no native equivalent needed |
| `pyodide` | Pyodide runtime mode, documented RO | Browser-runtime-specific |
| `show_semantics_debugger` | Accessibility semantics visualization | Requires a semantics/accessibility model |
| `test` | Client test mode, documented RO | Define local test mode only if it has concrete behavior |
| `wasm` | WebAssembly mode, documented RO | Browser-runtime-specific |

### Session, navigation, runtime, and messaging: 12

| Property | Flet purpose / contract | Suggested Saturn treatment |
| --- | --- | --- |
| `auth` | RO authorization context | Separate optional authentication service |
| `executor` | RO page executor | Saturn uses workers internally; expose only with a stable scheduling contract |
| `loop` | RO page asyncio event loop | Could expose existing App loop deliberately |
| `multi_view` | Client multi-view mode, documented RO | Requires multi-view lifecycle support |
| `multi_views` | Hosted multi-view collection | Requires coordinated native view/window management |
| `name` | RO session-provided page name | Optional local application/page identity |
| `pubsub` | RO page publication/subscription client | Optional messaging service |
| `query` | RO route query accessor | Depends on navigation/URL support |
| `route` | Current route, documented RO | Use a navigation API if implementing routes |
| `session` | RO connected session object | Flet transport concept; Saturn has a local App instead |
| `url` | RO session URL | No URL is inherent to a native Saturn window |
| `web` | Browser mode, documented RO | Saturn is currently a native framework |

### Additional events: 15

| Property | Flet event | Suggested Saturn treatment |
| --- | --- | --- |
| `on_app_lifecycle_state_change` | Application lifecycle changes | Map native visibility/focus/minimization as supported |
| `on_close` | Session expiration | Do not confuse with a native window-close event |
| `on_connect` | Web session connection | Transport-specific; should not be a dummy native field |
| `on_disconnect` | Web session disconnection | Transport-specific |
| `on_error` | Unhandled application errors | Add centralized error reporting if needed |
| `on_locale_change` | Host locale changes | Pair with locale support |
| `on_login` | OAuth result | Pair with optional authentication |
| `on_logout` | Logout completion | Pair with optional authentication |
| `on_media_change` | Media metrics changes | Pair with density/inset metrics |
| `on_multi_view_add` | Hosted view added | Pair with multi-view management |
| `on_multi_view_remove` | Hosted view removed | Pair with multi-view management |
| `on_platform_brightness_change` | System brightness changes | Useful for automatic SYSTEM theme updates |
| `on_route_change` | Route changes | Pair with optional navigation |
| `on_view_pop` | View back navigation | Pair with a View stack |
| `on_views_pop_until` | Stack pop reaches its destination | Pair with a View stack |

These groupings are for readability, not separate compatibility requirements.

## 3. Saturn properties absent from Flet Page: all 19

| Property or properties | Saturn Page behavior |
| --- | --- |
| `renderer` | Working Saturn-specific RO settings wrapper. `anti_aliasing` and `vsync` are strict boolean RW settings; `context` is the RO active backend renderer |
| `align`, `margin`, `left`, `top`, `right`, `bottom` | Inherited fields. Page layout uses the whole client viewport rather than these root geometry settings |
| `rotate`, `scale`, `offset` | Inherited fields. Root rotation/scale are not applied; offset uses the zero-sized root rect and has no normal visual displacement |
| `animate_opacity`, `animate_size`, `animate_position`, `animate_align`, `animate_margin`, `animate_rotation`, `animate_scale`, `animate_offset` | Inherited settings. Page prepares/ticks animations on children and overlays, not on the Page root itself |
| `on_animation_end` | Inherited callback field; no normal root animation lifecycle is driven |

These inherited fields should be documented as inactive at the Page root, implemented deliberately, or rejected there. They should not inflate a list of supported Page features. See [Renderer settings](./rendering.md) for the working renderer API.

## 4. Nested `page.window` comparison

Flet Window has **39** public properties including inherited `data`, `key`, `parent`, and `page`. Saturn Window has **7**. Six names overlap, 33 are Flet-only, and `title` is Saturn-only at this nested level.

### Six shared names

| Property | Flet | Saturn difference |
| --- | --- | --- |
| `width` | Native outer width, initial `None` | App outer width, initially 800; setting queues a client-size adjustment |
| `height` | Native outer height, initial `None` | App outer height, initially 600; setting queues a client-size adjustment |
| `icon` | Optional native icon path | Loads an image path or resets to the default icon |
| `maximized` | Native state field | Getter returns a cached requested flag; user actions are not mirrored |
| `minimized` | Native state field | Same cached-state limitation |
| `full_screen` | Native fullscreen state | Same cached-state limitation |

Saturn also has `window.title`; Flet controls the title through `page.title`. Saturn's two title paths are currently not synchronized in both directions.

### All 33 Flet-only Window names

| Area | Missing properties |
| --- | --- |
| Position and bounds | `top`, `left`, `max_width`, `max_height`, `min_width`, `min_height`, `aspect_ratio`, `alignment` |
| Window capabilities | `minimizable`, `maximizable`, `resizable`, `movable` |
| Visibility, stacking, and input | `focused`, `visible`, `always_on_top`, `always_on_bottom`, `ignore_mouse_events` |
| Decoration and appearance | `bgcolor`, `opacity`, `brightness`, `title_bar_hidden`, `title_bar_buttons_hidden`, `frameless`, `shadow`, `badge_label`, `progress_bar` |
| Close/taskbar behavior and event | `prevent_close`, `skip_task_bar`, `on_event` |
| Inherited identity/metadata | `data`, `key`, `parent`, `page` |

Saturn's native window is created resizable internally, but assigning `page.window.resizable` does not control that capability. The same principle applies to other missing fields. Implement actual SDL/platform calls before exposing them.

Flet's native close event is `window.on_event` with the close event type. Its `page.on_close` has session-expiration semantics. Saturn currently closes the App directly on native close and exposes neither event hook.

## 5. Suggested alignment checklist

These are proposed fixes, not completed changes. They preserve a simple native API and can be handled independently.

### Priority 1: fix misleading same-name properties

- [ ] Accept a single callback for `on_resize` and `on_keyboard_event`, with small typed event payloads. Retain handler-list registration deliberately if backward compatibility is needed.
- [ ] Normalize `Page.padding` to four edges and support numeric, Padding, and `None` values with documented defaults.
- [ ] Reconcile attachment after direct `controls`/`overlay` mutation during `update()`, so child events and updates work consistently.
- [ ] Select `theme` versus `dark_theme` according to mode, and invalidate colors/fonts when the effective theme changes.
- [ ] Define minimal service registration/lifecycle behavior or explicitly report the inert list as unsupported. Flet auto-registers services through the current Page context, rather than through assignment to `Page.services`.
- [ ] Refresh font alias registration after dictionary changes, or expose a documented registration API.
- [ ] Unify App, Page, and Window title state, including the initial title.

### Priority 2: clarify root and native contracts

- [ ] Define root `page` identity and parent mutability.
- [ ] Define how root visible/disabled/opacity affect background, overlays, and keyboard input.
- [ ] Document or reject inactive inherited root geometry and animation fields.
- [ ] Synchronize cached native state after user minimize/maximize/fullscreen actions.
- [ ] Add useful native properties first: resize capability, position, minimum/maximum sizes, topmost state, and a native window event hook.
- [ ] Expose platform/density information and update SYSTEM theme after OS preference changes.

### Optional scope extensions

- [ ] Implement root scrolling or document using the existing `ListView` for scrollable content.
- [ ] Add app bar, navigation, drawer, and FAB layout slots only when needed.
- [ ] Consider views/routes, locale/RTL, and accessibility as separate features.
- [ ] Keep web session/auth/URL/browser-only properties optional; native Saturn does not need placeholder fields for them.

## 6. Reproduce the name inventory

This small inspection recipe reproduces the 86/45 property counts without opening a window. It reads declarations and initialized state rather than accepting arbitrary attributes as supported API.

```python
import dataclasses
from types import SimpleNamespace
import flet
import saturn


def properties(cls):
    return {
        name
        for base in cls.__mro__
        for name, value in vars(base).items()
        if not name.startswith("_") and isinstance(value, property)
    }


flet_names = properties(flet.Page) | {
    field.name for field in dataclasses.fields(flet.Page)
    if not field.name.startswith("_")
}
app = SimpleNamespace(post=lambda callback: None, mark_dirty=lambda: None)
page = saturn.Page(app)
saturn_names = properties(saturn.Page) | {
    name for name in vars(page) if not name.startswith("_")
}
print(len(flet_names), len(saturn_names))
print("Shared:", sorted(flet_names & saturn_names))
print("Flet only:", sorted(flet_names - saturn_names))
print("Saturn only:", sorted(saturn_names - flet_names))
```

A different Flet version or Saturn revision can change this inventory. The source/behavior audit must also be repeated before treating matching names as compatible.

[Documentation home](./README.md) · [Startup comparison](./run-comparison.md) · [Compose verification](./compose.md)
