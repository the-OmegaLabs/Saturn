# Get started in five minutes

[← Documentation home](./README.md) · [API index](./api/README.md)

## Install and run

Python 3.10 or later is required. Development and testing currently focus on Windows.

```powershell
uv sync
uv run python examples/hello.py
```

## Your first window

```python
import saturn


def main(page: saturn.Page):
    page.title = "Hello Saturn"
    page.theme_mode = saturn.ThemeMode.DARK
    page.padding = 24

    message = saturn.Text("Hello, Saturn", size=24)

    def clicked(event: saturn.ControlEvent):
        message.value = "Button clicked"
        message.update()

    page.add(message, saturn.FilledButton("Click me", on_click=clicked))
    page.update()


saturn.run(main, backend=saturn.Render.SOFTWARE)
```

`saturn.run()` creates a window and passes a [`Page`](./api/Page.md) to `main`. Add controls with `page.add()`. After changing a control, call `control.update()` or `page.update()` to request a redraw. In a callback, `event.control` refers to the control that triggered the event.

## Change the rendering backend

```python
saturn.run(main, backend=saturn.Render.OPENGL)
```

You can also set `SATURN_BACKEND` when omitting the `backend` argument. `Render.VULKAN` is exported; availability depends on the local driver and current implementation.

## Keep exploring

- The [screenshot gallery](./gallery.md) shows the main controls.
- The [API index](./api/README.md) lists parameters and methods by category.
- The [Flet mapping and scope](./flet-mapping.md) helps with migration from Flet desktop apps.
