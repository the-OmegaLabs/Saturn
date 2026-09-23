<p align="center">
  <img src="./saturn-logo.svg" width="112" alt="Saturn logo">
</p>

<h1 align="center">Saturn</h1>

<p align="center">
  A modern, lightweight, GPU-accelerated desktop UI framework for Python.
</p>

<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-000000?style=flat-square&logo=python&logoColor=white">
  <img alt="Status: Alpha" src="https://img.shields.io/badge/status-alpha-000000?style=flat-square">
  <img alt="Software and OpenGL renderers" src="https://img.shields.io/badge/renderers-Software%20%7C%20OpenGL%20%7C%20Vulkan-000000?style=flat-square">
</p>

> **Saturn** is currently in **alpha** stages. Everything may change, some controls are still being completed, and production use should be evaluated carefully.

Saturn provides a familiar, declarative API for building native desktop interfaces while keeping rendering and the event loop local to the application.

Browse the [Saturn documentation](./saturn-docs/README.md) for API pages and a screenshot gallery.

Inspired by the simplicity of [Flet](https://flet.dev/), Saturn takes a **lighter and more local approach** to desktop UI development. It uses almost the same concepts and API patterns, while remaining an independent, minimal, and lightweight native UI framework with its own architecture and direction.

Because this compatibility is built into the API design, most Flet desktop applications can be migrated to Saturn with minimal changes, without depending on Flet's underlying implementation.

If you're looking to build a **web application**, [use Flet instead](https://flet.dev/).

## Preview

<table>
  <tr>
    <td align="center">
      <strong>Demo</strong><br>
      <img src="./shots/demo.png" width="440" alt="Saturn controls demo">
    </td>
    <td align="center">
      <strong>Layout</strong><br>
      <img src="./shots/layout-demo.png" width="440" alt="Saturn layout demo">
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong>Text</strong><br>
      <img src="./shots/text-demo.png" width="440" alt="Saturn text demo">
    </td>
    <td align="center">
      <strong>Widgets</strong><br>
      <img src="./shots/widgets-demo.png" width="440" alt="Saturn widgets demo">
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong>Buttons</strong><br>
      <img src="./shots/buttons-demo.png" width="440" alt="Saturn button variants">
    </td>
    <td align="center">
      <strong>Inputs</strong><br>
      <img src="./shots/inputs-demo.png" width="440" alt="Saturn input controls">
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong>Expressive</strong><br>
      <img src="./shots/expressive-dark.png" width="440" alt="Expressive controls with dark theme">
    </td>
    <td align="center">
      <strong>Demo</strong><br>
      <img src="./shots/demo.png" width="440" alt="Saturn controls with dark theme">
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong>Motion</strong><br>
      <img src="./shots/expressive-motion.png" width="440" alt="Expressive loading and motion controls">
    </td>
    <td align="center">
      <strong>FAB Menu</strong><br>
      <img src="./shots/expressive-menu.png" width="440" alt="Expanded floating action button menu">
    </td>
  </tr>
</table>

<p align="center">
  <i>Preview: not final.</i>
</p>

## Why

Saturn is built around a simple idea: **desktop UI development should be lightweight, easy to understand, and easy to extend.**

The API and architecture are intentionally kept **extremely simple, lightweight, and extensible**, with a focus on local rendering and a clear separation between the framework and the language it is implemented in.

Saturn takes inspiration from familiar declarative UI frameworks such as [Flet](https://flet.dev/), while developing its own approach to native desktop UI. By keeping the design language simple and implementation-independent, the same concepts can be brought to other programming languages in the future.

Unlike frameworks built around **Skia or WebView**, Saturn renders directly through the platform's **native graphics APIs**, avoiding unnecessary rendering layers and keeping the rendering pipeline lightweight and efficient.

That's our goal: **a small foundation that is easy to understand, extend, and port.**

## Requirements

- Python 3.10 or newer
- A desktop environment supported by SDL
- An OpenGL-capable driver when using the OpenGL backend

Saturn is still in its early stages and is currently developed and tested exclusively on Windows. Cross-platform support is planned for future releases as the project matures.

## Installation

Clone the repository and install its dependencies with [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/the-OmegaLabs/Saturn.git
cd Saturn
uv sync
```

Alternatively, install the project into an existing virtual environment:

```bash
python -m pip install -e .
```

## Quick start

```python
import saturn


def main(page: saturn.Page):
    page.title = "Hello Saturn"
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 24

    message = saturn.Text(
        "Hello from Saturn!",
        size=28,
        weight=saturn.FontWeight.BOLD,
        color=saturn.Colors.ON_SURFACE,
    )

    def handle_click(e):
        message.value = "It works!"
        message.update()

    page.add(
        message,
        saturn.FilledButton(
            "Click me",
            icon=saturn.Icons.AUTO_AWESOME,
            on_click=handle_click,
        ),
    )
    page.update()


saturn.run(main)
```
Controls are mutable. After changing a control's state, call `control.update()` or `page.update()` to schedule a redraw.

Or run the bundled hello example:

```bash
uv run python examples/hello.py
```

The API is intentionally simple and familiar, so writing Saturn applications feels almost the same as writing Flet applications.

## Rendering backends

Select a renderer when starting the application:

```python
# Portable CPU renderer
saturn.run(main, backend=saturn.Render.SOFTWARE)

# GPU-accelerated renderer
saturn.run(main, backend=saturn.Render.OPENGL)
```

The backend can also be selected with the `SATURN_BACKEND` environment variable when `backend` is omitted:

```powershell
$env:SATURN_BACKEND = "opengl"
uv run python examples/hello.py
```

## Implemented or partially implemented

| Category | Available controls |
|---|---|
| Layout | `Row`, `Column`, `Stack`, `Container`, `Card`, `Divider`, `ListView` |
| Content | `Text`, `Icon`, `Image` |
| Buttons | `Button`, `ElevatedButton`, `FilledButton`, `FilledTonalButton`, `OutlinedButton`, `TextButton`, `IconButton` |
| Inputs | `TextField`, `Checkbox`, `Switch`, `Radio`, `RadioGroup`, `Slider`, `Dropdown` |
| Feedback | `ProgressBar`, `ProgressRing`, `AlertDialog`, `SnackBar` |
| Interaction | `GestureDetector`, tooltips, pointer and keyboard events |
| Services | `FilePicker` |

The public API also includes theme, alignment, padding, border, shadow, animation, transform, text-style, and scrolling types.

## Examples

| Example | Description |
|---|---|
| [`examples/hello.py`](./examples/hello.py) | Minimal application and window lifecycle |
| [`examples/demo.py`](./examples/demo.py) | Combined control showcase |
| [`examples/layout_demo.py`](./examples/layout_demo.py) | Layout, alignment, expansion, and stacking |
| [`examples/inputs_demo.py`](./examples/inputs_demo.py) | Text fields, toggles, radios, sliders, and dropdowns |
| [`examples/buttons_demo.py`](./examples/buttons_demo.py) | Button variants and events |
| [`examples/text_demo.py`](./examples/text_demo.py) | Typography and text behavior |
| [`examples/widgets_demo.py`](./examples/widgets_demo.py) | Icons, images, cards, and progress indicators |
| [`examples/expressive_demo.py`](./examples/expressive_demo.py) | Expressive controls in light and dark themes |
| [`examples/expressive_motion_demo.py`](./examples/expressive_motion_demo.py) | Loading shapes, waves, toolbar, and FAB menu |

Run the full showcase with either renderer:

```bash
uv run python examples/demo.py
uv run python examples/demo.py --backend opengl
```

## Contributing

**Saturn** is an open-source project led by **Omega Labs**. Contributions, issues, and feature requests are welcome.

## License

License information will be announced later.
