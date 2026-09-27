# Saturn performance issues and fixes

Updated: 2026-09-27. Optimizations stay in the existing controls; no `VirtualStudentList` is introduced. The original measurements below were recorded on 2026-09-23. The follow-up section records new measurements and acceptance checks from 2026-09-27.

## Completed

- [x] **Default backend selection.** `saturn.run()` defaults to `Renderer.OPENGL`, with GPU primitives and batching. `Renderer.SOFTWARE` and `Renderer.VULKAN` remain explicit choices. Application entry scripts can override the default.
- [x] **Invisible list items still drawn and hit-tested.** The original `ListView` clipped pixels but visited every control. It now uses sorted row coordinates and binary search to select draw, layout, and hit-test candidates within the viewport plus a 96 logical pixel preload margin, expanded for declared paint overflow. Control objects and event interfaces are preserved.
- [x] **Scrolling and hovering trigger full-page layout.** `Page` separates layout updates from repaint requests; animations advance only active controls. Fixed-height rows and `item_extent` place subtrees on demand in the existing `ListView`. Resize reuses vertical positions and places nearby rows.
- [x] **OpenGL allocates and submits a buffer for each rectangle.** Consecutive rectangles are batched in drawing order with reusable VBO/VAO resources. Texture changes still preserve alpha composition order.
- [x] **OpenGL viewport returns to native pixel size after resize.** SDL can change the GL viewport outside ModernGL's cache, shifting 2x offscreen rendering into the lower-left corner. Each clear now binds the offscreen target and explicitly restores its viewport. A regression simulates an external `glViewport` change.
- [x] **Hidden controls and moved carets leave blinking trails.** OpenGL previously kept blending enabled when copying the completed frame into the window. Translucent pixels mixed with the previous frame and old positions faded gradually. Final resolve now disables blending, replaces the whole window, and restores drawing state. In the two-frame reproduction, the old caret pixel changed from residual `(78, 78, 78)` to the exact background `(39, 39, 39)`. `tests/input_checks.py` checks moved carets and hidden controls with pixels.
- [x] **Text and caret are vertically misaligned.** Consolas 14 value and hint ink sat about 2 pixels above the caret's visual center. `TextField` now measures a stable reference glyph for each family, size, and scale and caches its baseline correction. Value, hint, selection, and IME underline align together; caret and IME candidate anchor retain their positions. The unintended horizontal spacing change was reverted. Hidden OpenGL pixel checks cover Consolas 14 and the default font, with both hints and values.
- [x] **Static bitmaps are read and hashed every frame.** Immutable text, icon, and image surfaces use bounded identity-based texture caches. Icon raster results are reused; OpenGL scales images directly.
- [x] **Repeated text measurement and wrapping.** Text metrics, recent widths, and font sources are cached. Changes to text, width, or font still invalidate the result.
- [x] **Ordinary hover overlays allocate CPU bitmaps.** OpenGL draws uniform-radius hover layers without ripples as translucent GPU rectangles. Irregular corners and the software backend retain their precise mask paths.
- [x] **Pressed ripples allocate CPU bitmaps.** An OpenGL shader primitive computes four-corner masks and dynamic ripples in drawing order, without creating, hashing, or uploading a Surface. Software retains its original path. Against software, the 200 x 100 ripple region had mean pixel difference about 1.03/255 and maximum 16/255. Ripple stress checks pass on all three backends. A single ripple did not materially improve total frame time; the concrete gain is removing its dynamic bitmap path.
- [x] **Variable-height rows are repeatedly placed and measured.** The existing `ListView` places only nearby subtrees and caches exact row coordinates for the last three widths. Built-in `Container` reuses measured height across widths when natural content width already fits; wrapping rows still use actual width. Content updates invalidate the cache. A 5,000-row continuous-width test reduced p95 from about 159 ms to about 14 ms.
- [x] **Vulkan draws the whole frame on the CPU before uploading it.** SPIR-V shaders, a Vulkan render pass, and GPU vertex batches now draw rectangles, lines, circles, textures, and clipped regions. Adjacent primitives sharing texture and clip are batched. Screenshots read back from the GPU on demand. Text and a few complex effects still generate small CPU textures, but the full frame is no longer rasterized on the CPU. `tests/vulkan_checks.py` forces the old software drawing and whole-frame upload paths to fail; real-window background, rectangle, and texture pixel checks pass.
- [x] **Vulkan allocates separate GPU images for newly encountered text during large jumps.** A bounded 1024-square texture atlas uses 1-pixel transparent padding and grouped region uploads. It caches immutable text and icons without changing list structure. A 5,000-row, 60-frame full-list jump test reduced p95 from **26.51 ms** to **6.68 ms**; ordinary drawing and ripple checks still pass.
- [x] **Vulkan diagonals, arcs, and control edges lack antialiasing.** Supported device and format capabilities choose 4x, 2x, or 1x sampling; a multisampled color attachment resolves into the swapchain. Rounded-rectangle SDF feathering was adjusted toward OpenGL. This machine used 4x: blended diagonal edge pixels rose from 0 at 1x to 133, and arc pixels from 0 to 236. Rounded corners and text also approached OpenGL's blended edge counts. Vulkan checks include diagonal and arc pixel regressions.
- [x] **SVG and large PNG edges alias when reduced.** Geometry MSAA does not filter texture interiors. `Image` rasterizes SVG at the target device pixel size and caches a smooth reduction of large PNGs before GPU composition. The 410 x 304 demo logo no longer relies on a single bilinear reduction to about 52 x 40. `tests/image_antialias_checks.py` checks target size, real SVG pixels, and cache reuse. `.static/shots/demo-vulkan.png` is the actual Vulkan screenshot after the fix.
- [x] **Measured the cost of the 2x offscreen framebuffer.** OpenGL GPU queries for 5,000 rows measured p50 around 3.31 / 3.33 ms at 1x / 2x. No stable speed gain was observed, so 2x remains the default for text and corner quality.
- [x] **Repeated property reads slow list layout.** A profile recorded over 110,000 `Control.__getattribute__` calls during one `_place` at a new width. The `ListView` row loop now reads required raw properties and animation overrides once while preserving animation semantics. Global property access is unchanged.
- [x] **Duplicate attach.** Redundant subtree attachment was removed; event and animation regressions pass.
- [x] **Renderer settings are unavailable through Page.** `page.renderer.anti_aliasing` and `page.renderer.vsync` accept booleans and default to `True`; `page.renderer.context` exposes the actual renderer. Changes are coalesced on the UI thread. Real software, OpenGL, and Vulkan windows passed option toggling, resize, and pixel checks. On this machine Vulkan toggled 1x/4x samples and immediate/FIFO presentation. See [Renderer settings](docs/rendering.md) for fallback behavior and the scope of antialiasing.

## Completed follow-up work (2026-09-27)

- [x] **Reduce initial variable-height layout overhead.** Exact single-line text measurement, shared font lookup caches, and fewer property reads reduce the existing list's initial cost. Three independent software-window comparisons of 5,000 rows measured median cold layout **256.867 → 127.638 ms** (50.3% lower), and cold first frame **298.081 → 169.827 ms**. Row heights and scroll extent remain exact; no estimated heights or replacement list are used. `tests/list_layout_checks.py` verifies variable heights at four widths and content invalidation.
- [x] **Cull using declared paint overflow.** Shadows, Material elevation, offsets, nested descendants, absolute positions, and animation targets expand the local candidate range beyond 96 pixels. Ordinary rows keep the binary-search path. Pixel comparisons against uncropped drawing cover a 180-pixel blur, elevation 80, far offsets, nested/horizontal controls, width changes, and property updates; fixtures also prove that the old fixed margin omitted visible pixels.
- [x] **Remove measured dynamic bitmap hotspots.** OpenGL and Vulkan draw LoadingIndicator geometry, analytic wavy progress, and Material elevation shadows on the GPU. Icon/image tint and bitmap enlargement reuse source textures. `tests/dynamic_renderer_checks.py` rejects CPU Surface creation during animation and pixel hashing during repeated tint changes, and verifies silhouettes, clipping, opacity, and resize. This removes per-frame bitmap allocation/uploads for the covered controls.
- [x] **Smooth Vulkan lines and arcs at 1x sampling.** Interpolated coverage meshes feather triangle boundaries independently of hardware MSAA. Forced 1x real-window checks produce **178 diagonal / 224 arc blended edge pixels**. Rounded shapes retain analytic edge coverage. MSAA remains enabled when supported.
- [x] **Align useful Page behavior.** Fonts accept local/assets paths and HTTP(S), including TTF/OTF/TTC/WOFF/WOFF2. Dictionary mutation, completed downloads, and removals invalidate layout and rendered caches. Typed keyboard, resize, and brightness events accept single/list callbacks, sync/async handlers, and zero/one argument. Direct list mutations, service ownership, asymmetric padding, effective dark themes, disabled input, title state, and measured display density are covered by `tests/page_compatibility_checks.py`.
- [x] **Complete native Window properties and HWND access.** All 39 inspected shared public Window names are exposed, plus `title`, `hwnd`, and `native_handle`. Windows native checks cover sizing/limits, styles, fullscreen/state, positioning/centering, opacity/color key, taskbar progress/badge resources, and close interception. Advanced Windows-only settings fail explicitly on other platforms. See [Native windows](docs/window.md) and [Page comparison](docs/page-properties-comparison.md).

### Practical constraints

- Unknown variable row heights still require an O(N) initial exact measurement. The measured cost is reduced, not eliminated. Known-height data can use child `height` or `ListView.item_extent` to avoid intrinsic measurement.
- Culling can account for declared built-in geometry. Custom drawing that extends beyond a control without declaring bounds needs a corresponding overflow rule and a pixel regression.
- Initial image decoding, font/SVG rasterization, and high-quality bitmap reduction still use CPU source processing and cached textures. The full OpenGL/Vulkan frame and the dynamic effects above are rasterized on the GPU.
- GPU elevation shadows approximate the original blur. Windows background transparency is color-keyed, not per-pixel desktop alpha. Other platform limits are documented in the Window guide.

### Follow-up measurements

A sequential 5,000-row, 40-frame variable-height resize sweep measured software /
OpenGL / Vulkan draw-and-present p95 **10.487 / 11.910 / 13.136 ms**, with at most
22 rows drawn. Window/attachment setup p95 was **2.449 / 2.530 / 10.238 ms**.

A separate 24-control animation comparison measured old bitmaps → GPU p95
**7.565 → 5.069 ms** on OpenGL and **9.024 → 7.951 ms** on forced-1x Vulkan.
These are local wall-clock observations; driver scheduling and machine load vary.
The concrete invariant is removal of the covered dynamic CPU bitmap paths.

## Stress evidence and commands

`tests/performance_stress.py` creates real windows, renderers, and 5,000 controls. It replays scrolling, hover, full-list jumps, ripples, and resize. Windows are hidden by default; `--visible` briefly shows a real window and `--gpu-time` gathers OpenGL GPU queries. Results vary with drivers and machine load.

```powershell
.venv\Scripts\python.exe tests\performance_stress.py --backend all --rows 5000 --frames 60
.venv\Scripts\python.exe tests\performance_stress.py --backend opengl --rows 5000 --frames 60 --resize-every 2
.venv\Scripts\python.exe tests\performance_stress.py --backend opengl --rows 5000 --frames 60 --full-sweep --resize-every 2
.venv\Scripts\python.exe tests\performance_stress.py --backend opengl --rows 5000 --frames 60 --ripple --gpu-time
.venv\Scripts\python.exe tests\performance_stress.py --backend opengl --rows 5000 --frames 60 --resize-every 2 --visible
.venv\Scripts\python.exe tests\performance_stress.py --backend opengl --rows 5000 --frames 60 --variable-height --resize-sweep
.venv\Scripts\python.exe tests\performance_stress.py --backend vulkan --rows 5000 --frames 60 --resize-every 2
.venv\Scripts\python.exe tests\performance_stress.py --backend vulkan --rows 5000 --frames 60 --full-sweep
.venv\Scripts\python.exe tests\vulkan_checks.py
.venv\Scripts\python.exe tests\image_antialias_checks.py
.venv\Scripts\python.exe tests\renderer_options_checks.py
.venv\Scripts\python.exe tests\page_compatibility_checks.py
.venv\Scripts\python.exe tests\window_checks.py
.venv\Scripts\python.exe tests\list_layout_checks.py
.venv\Scripts\python.exe -m tests.dynamic_renderer_checks --stress
```

Local 800 x 600, 5,000-row, 60-frame continuous scroll: OpenGL drawing plus presentation p50 **2.83 ms**, p95 **3.14 ms**; software p50 **3.93 ms**, old CPU Vulkan p50 **4.87 ms**. About 20 of 5,000 rows entered drawing. Resize alternated 800 x 600 and 760 x 570 every two frames: OpenGL before optimization p50 **9.20 ms**, p95 **18.59 ms**, after optimization **1.21 / 2.07 ms**, plus about 2-4 ms of window/framebuffer setup. After GPU hover primitives on 2026-09-23, the same scenario measured **1.67 / 2.55 ms**. Machine and cache variations prevent attributing that difference solely to hover changes. Full-list jumps with resize measured **4.42 / 7.24 ms**.

Visible-window resize replay measured drawing plus presentation p50 **1.47 ms**, p95 **2.40 ms**, with window/framebuffer setup p95 **6.03 ms**. Ripple stress supports three backends. OpenGL GPU ripple p95 was **3.15 ms**, versus **3.18 ms** with the old CPU ripple path forced; the single-ripple difference was not clear on this machine.

Before the Vulkan GPU rewrite, another 5,000-row, 60-frame run measured fixed-height drawing plus presentation p95 **3.41 ms** for OpenGL, **3.97 ms** for software, and **7.76 ms** for old CPU Vulkan, with about 20 drawn rows per frame. Variable heights alternating two widths measured OpenGL p95 **3.48 ms** and window setup **4.18 ms**. An 81-width drag simulation measured **14.14 ms** and setup **2.42 ms**.

After the Vulkan GPU rewrite, local 5,000-row, 60-frame drawing plus presentation measured p50 **3.07 ms**, p95 **3.58 ms**, with presentation p50 **1.10 ms**. Resize every two frames measured drawing plus presentation p95 **4.81 ms**, swapchain setup **11.61 ms**. Default OpenGL in the same resize workload measured **1.89 ms**, framebuffer setup **4.26 ms**. These hidden-window wall-clock measurements are not bounds for every GPU or window manager.

With Vulkan 4x MSAA, ordinary scrolling measured p50 **3.04 ms**, p95 **5.80 ms**, including occasional GPU scheduling tails. Resize measured drawing plus presentation p95 **3.69 ms**, swapchain setup **12.81 ms**; ripple p95 **3.15 ms**, full-list jumps **7.55 ms**. Antialiasing adds GPU sampling and resize attachment costs.

The final sequential 5,000-row, 60-frame ordinary scroll run measured software/OpenGL/Vulkan drawing plus presentation p95 **5.48 / 3.29 / 3.19 ms**, with about 20 rows drawn per frame. Variation from the previous Vulkan result reflects scheduling and machine state; identical results on every run are not guaranteed.

Full-list jumps encounter many different text textures for the first time. Vulkan p95 fell from **26.51 ms** to **6.68 ms** with the small-texture atlas; OpenGL measured **3.87 ms**. This stresses cold texture creation more than ordinary continuous scrolling.

## Other requested work

- [x] Migrated `saturn-docs` into `docs`; retained and updated the useful `docs/expressive.md`.
- [x] Removed `references`; README, NOTICE, and the bundled Apache 2.0 license retain origins and attribution.
- [x] Added `saturn.Compose` and [migration and Flet verification notes](docs/compose.md). Installed Flet 1.0.1 verification covers 68 shared class signatures, 29 standard constructors, and 4 behavior paths. Full Flet behavior compatibility remains outside the implemented scope; gaps are documented.
- [x] Named the public backend enum `saturn.Renderer`; retained `saturn.Render` as a compatibility alias.
- [x] Moved screenshots, logos, and documentation control images into `.static` and updated references. Removed unused local one-off scripts.
- [x] Retained `gen/MaterialSymbolsOutlined.codepoints`, which remains an input to `gen_enums.py`. Referenced tests, tools, and generators remain.
- [x] Removed startup `width`/`height`; use `page.window` instead. Unsupported startup options raise `TypeError`. [Startup comparison](docs/run-comparison.md) covers Saturn and installed Flet 1.0.1.
- [x] Removed Flet wording and internal names from the `saturn` package; comparative API documentation retains factual references.
- [x] Converted repository documentation to English, including the feature planning notes below.

# Saturn and Qt feature-gap planning notes

These notes describe desktop UI capabilities to consider over time. They are a planning reference, not a claim that every listed API is implemented or an instruction to implement all of them in the current optimization work.

## 1. Model / View data models

Qt provides a mature Model/View architecture, including `QAbstractItemModel`, `QModelIndex`, `QSortFilterProxyModel`, `QTableView`, `QTreeView`, and `QListView`. Models own data; views display it.

A file manager can use this flow:

```text
File system -> File Model -> TreeView
```

Large datasets do not need to become UI controls all at once. Saturn currently favors direct control manipulation and lacks a mature equivalent abstraction. Model/View provides a foundation for IDEs, file managers, database tools, and log viewers.

## 2. Table

Qt's table system supports rows, columns, headers, sorting, filtering, multiple selection, cell editing, custom cells, and large-data virtualization.

```text
Name       Size      Modified
test.py    12 KB     Today
main.cpp   48 KB     Yesterday
app.exe    2 MB      Monday
```

Saturn can compose similar interfaces from existing controls, but needs a dedicated efficient Table for database managers, IDEs, system tools, and administration interfaces.

## 3. Tree

Qt's TreeView supports arbitrary nesting, expansion and collapse, node selection, node dragging, lazy loading, and many nodes.

```text
Project
├── src
│   ├── main.py
│   └── app.py
├── assets
│   └── icon.png
└── README.md
```

Saturn lacks a dedicated Tree / TreeView data structure. File managers, IDEs, asset browsers, and project management tools commonly need it.

## 4. Canvas / custom drawing

Qt supports custom lines, rectangles, circles, paths, images, text, and other shapes. A possible Saturn interface would expose:

```text
Canvas
├── line()
├── rect()
├── circle()
├── path()
├── image()
└── text()
```

Users could implement specialized controls without waiting for built-in widgets. Canvas would support charts, drawing applications, node editors, audio waveforms, game editors, CAD, and data visualization.

## 5. Native Window API

Qt offers window size and position, minimum and maximum sizes, fullscreen, frameless and transparent windows, always-on-top behavior, and native handles. Saturn now implements the corresponding native desktop settings, with the platform and transparency limits described in [Native windows](docs/window.md):

```text
page.window.title
page.window.width / height
page.window.left / top
page.window.full_screen
page.window.resizable
page.window.bgcolor / opacity
page.window.native_handle
page.window.hwnd
```

The Windows native handle is an HWND. These advanced capabilities matter for desktop tools, game launchers, OBS-style applications, desktop overlays, and system utilities, even when ordinary applications do not need them.

## 6. Native Menu

Qt provides menu bars, menus, submenus, menu items, and shortcuts.

```text
File
├── New
├── Open
├── Save
└── Exit
```

A possible Saturn hierarchy is `MenuBar -> Menu -> MenuItem`, with multiple menus and items. IDEs, editors, engineering applications, file managers, and professional tools rely on menus.

## 7. System Tray

Qt's `QSystemTrayIcon` supports tray icons, menus, notifications, clicks, and double-clicks.

```text
[ Saturn Icon ]
├── Show
├── Settings
└── Exit
```

Downloaders, synchronization tools, AI agents, server managers, and music players often run without a continuously visible window.

## 8. Native Dialog

Qt provides system dialogs for opening and saving files, selecting folders, colors and fonts, and displaying messages.

```text
Open File
┌────────────────────────────┐
│ Documents                  │
│ Downloads                  │
│ test.py                    │
│ [Cancel]        [Open]     │
└────────────────────────────┘
```

Saturn already has file selection capabilities. Native Dialog APIs could be expanded so users receive familiar operating-system dialogs.

## 9. Clipboard

Qt supports clipboard text, images, HTML, files, and MIME data. A basic example is `clipboard.set_text("Hello")`; richer formats should also be supported. Copy and paste are fundamental desktop capabilities.

## 10. Drag & Drop

A complete drag-and-drop system handles incoming files, text, URLs, and MIME data, and allows controls to become drag sources.

```text
User drags a file -> Saturn -> Drop Event
```

File managers, IDEs, image editors, and asset browsers rely on this interaction.

## 11. Multiple windows

Qt manages multiple windows, including modality, dialogs, parent/owner relationships, lifecycle, and activation state.

```text
Main Window
├── Settings
├── About
└── Editor
```

Complex desktop applications often need several coordinated windows.

## 12. Multiple monitors

Qt abstracts monitor identity, resolution, DPI, scale factor, position, and the primary monitor.

```text
Monitor 1: 1920 x 1080 @ 100%
Monitor 2: 2560 x 1440 @ 150%
```

Two- and three-monitor setups require correct position and density handling to avoid excessively small or large UI and offscreen windows.

## 13. DPI / HiDPI

A mature density system handles per-monitor DPI, density changes, scale factors, and dynamic updates. Moving a window from 100% to 150% requires recalculating dimensions. Modern Windows, macOS, and Linux desktop applications need reliable support.

## 14. Keyboard Shortcut System

Qt supports shortcuts such as `Ctrl+S`, `Ctrl+O`, `Ctrl+Shift+P`, and `F5`, scoped to a window, widget, or application. IDEs, editors, and professional tools need this mechanism.

## 15. Focus System

A focus chain allows Tab navigation:

```text
TextField -> TextField -> Button -> Checkbox
```

Focus policies, scopes, and keyboard navigation support forms and accessibility. Saturn should provide consistent focus management.

## 16. Event System

Qt's event system covers mouse, keyboard, touch, gestures, windows, focus, drag-and-drop, clipboard, IME, and native events. Event filters can intercept events. This breadth supports mature desktop applications.

## 17. Custom Widget API

Qt allows application-defined widgets such as `class MyWidget(QWidget)`, with custom layout, event handling, painting, state, and properties. Saturn should progressively expose comparable extension points because built-in controls cannot cover every use case.

## 18. Style / Theme Engine

Qt styles cover buttons, text fields, menus, scrollbars, windows, focus, hover, pressed, and disabled states. Saturn already has themes; a systematic style engine could apply a coherent appearance across an application without individual control configuration.

## 19. Animation System

Property animations can target position, size, opacity, color, transforms, and custom properties.

```text
opacity: 0 -> 1
duration: 200 ms
easing: ease_out
```

A shared animation system supports complex interfaces without separate timing implementations in each control.

## 20. Resource System

Qt resources manage images, SVGs, fonts, icons, shaders, and other assets and can package them inside an application. Published applications should not depend on paths from the development environment.

## 21. Font System

A complete font system handles families, weights, fallback, Unicode, loading, metrics, and letter spacing. Mixed Chinese, English, Japanese, Korean, and emoji text needs correct fallback. Text rendering is a complex GUI subsystem.

## 22. Internationalization

Qt supports translation, locale, right-to-left text, number formatting, and date formatting. Applications can switch among English, Chinese, Japanese, and Korean based on locale. International desktop use requires these capabilities.

## 23. Accessibility

Desktop accessibility includes screen readers, accessible names and roles, keyboard navigation, and UI automation. A displayed button label should have corresponding system metadata:

```text
Role: Button
Name: "Click"
State: Enabled
```

These interfaces are needed for professional desktop applications and assistive technology.

## 24. File System Model

Qt can expose a filesystem model through a tree view and watch filesystem changes.

```text
FileSystemModel -> TreeView

C:\
├── Users
├── Windows
└── Program Files
```

This is useful for file managers, IDEs, and asset browsers.

## 25. GPU / Graphics API extensions

Qt offers OpenGL, Vulkan, QRhi, scene graphs, and shaders. Saturn already has software, OpenGL, and Vulkan renderers. Additional low-level interfaces could expose textures, shaders, framebuffers, render targets, and GPU resources. Accessible GPU functionality could help distinguish Saturn's Python desktop API.

## 26. Plugin System

Qt can load plugins dynamically. Saturn extension categories could include renderer, widget, backend, and other extension plugins. Third-party developers should be able to extend functionality without modifying core code.

## 27. UI Designer

Qt Designer supports dragging widgets into layouts and editing properties to build interfaces. Saturn currently favors code-driven UI. A lightweight Saturn Designer could help non-programmers and speed up complex layout prototyping.

## 28. Native Platform Backend

Qt provides mature platform abstractions:

```text
Windows -> Win32
Linux   -> X11 / Wayland
macOS   -> Cocoa
```

Saturn development and testing currently focus on Windows. Cross-platform support requires correct window behavior, IME, DPI, menus, fonts, and accessibility, in addition to successful startup.

## 29. Testing Infrastructure

GUI frameworks need widget, event, rendering, screenshot, DPI, input, and cross-platform tests. Renderer changes should preserve software, OpenGL, and Vulkan behavior. Regressions can otherwise appear in unrelated controls when one area changes.

## 30. Ecosystem

An ecosystem includes third-party widgets and libraries, tutorials, documentation, examples, plugins, IDE integration, and a community. Saturn does not need Qt's scale immediately, but should support installation and import of third-party extensions:

```python
# Install first: pip install xxx
import xxx
```

## Suggested roadmap

The framework need not implement all thirty areas at once. A possible order is:

1. Model / View
2. Table
3. Tree
4. Canvas
5. Native Window
6. Menu / Context Menu
7. Clipboard
8. Drag & Drop
9. Multiple Windows
10. DPI / HiDPI
11. Focus / Keyboard
12. IME
13. Accessibility
14. File System Model
15. GPU API
16. Plugin API
17. Cross-platform Backend

The proposed layers are:

```text
┌─────────────────────────────┐
│          Saturn API         │
├─────────────────────────────┤
│ Widgets / Layout / Theme    │
├─────────────────────────────┤
│ Model / View / Canvas       │
├─────────────────────────────┤
│ Event / Input / IME         │
├─────────────────────────────┤
│ Window / Native Integration │
├─────────────────────────────┤
│ Renderer                    │
│ Software / OpenGL / Vulkan  │
├─────────────────────────────┤
│ Platform                    │
│ Windows / Linux / macOS     │
└─────────────────────────────┘
```

The proposed direction is a Python desktop UI framework with a simple API, local rendering, GPU support, and progressively accessible lower-level capabilities. The reference frameworks inform planning without requiring Saturn to reproduce their entire scope.
