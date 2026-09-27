# Saturn.run and Flet.run

Verified on 2026-09-27 against the installed **Flet 1.0.1** signature and source in `flet/app.py`, and the Saturn implementation in this repository.

## Window dimensions

Neither `run()` accepts `width` or `height`. Set dimensions through `page.window` in the entry function:

```python
import saturn as ft


def main(page: ft.Page):
    page.window.width = 960
    page.window.height = 800
    page.title = "My app"
    page.add(ft.Text("Hello"))


ft.run(main)
```

The window configuration syntax also works with `import flet as ft`. `page.window.width/height` describe the native outer window, while `page.width/height` describe its content area. Saturn starts with an 800 x 600 window when no dimensions are set.

## Entry point differences

Saturn's signature:

```python
saturn.run(main, *, backend=None, title="saturn")
```

| Feature | Saturn | Flet 1.0.1 |
| --- | --- | --- |
| `main(page)` | Functions, bound methods, and coroutines | Functions, bound methods, and coroutines |
| `width`, `height` | Rejected; use `page.window` | Rejected; use `page.window` |
| `backend` | OpenGL, Vulkan, or software; defaults to OpenGL, overridable with `SATURN_BACKEND` | No such parameter |
| `title` | Initial title; can also be changed through `page.title` | No startup parameter; use `page.title` |
| `before_main` | Unsupported; raises `TypeError` | Called after creating Page and before running main |
| `name`, `host`, `port`, `view` | Unsupported; raises `TypeError` | Configure application name, service address, and presentation mode |
| `assets_dir`, `upload_dir` | Unsupported; resources use actual file paths | Configure asset and upload directories |
| `web_renderer`, `route_url_strategy`, `no_cdn` | Unsupported | Configure web rendering and routing |
| `export_asgi_app` | Unsupported | Can return a FastAPI ASGI application |
| Return value | Returns `App` after the window closes | Normally `None`; ASGI export returns an application |
| Execution | SDL window loop; ordinary callbacks run in workers, coroutines in a background asyncio loop | Starts socket or web transport according to presentation mode; ordinary `run()` uses asyncio startup |

Saturn no longer silently accepts arbitrary startup keywords. Unsupported parameters raise an error; use the table above when migrating.

Pass an instance's bound method, for example `ft.run(Application().create_window)`. Passing the unbound `Application.create_window` leaves its `page` argument missing when the runtime supplies the Page as the first argument.

[Documentation home](./README.md) · [run API](./api/run.md) · [Renderer settings](./rendering.md)
