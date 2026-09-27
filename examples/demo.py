"""Full Saturn demo showing the core controls together.

Run with:
    uv run examples/demo.py                          # Web
    uv run examples/demo.py --port 12342             # Web, preferred port
    uv run examples/demo.py --backend opengl         # Native OpenGL
    uv run examples/demo.py --backend vulkan         # Native Vulkan
"""
import argparse

import saturn
import saturn.web

from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header, demo_panel


class Application:
    def create_window(self, page: saturn.Page):
        page.window.width = DEMO_WIDTH
        page.window.height = DEMO_HEIGHT
        page.title = "saturn demo"
        page.theme_mode = saturn.ThemeMode.DARK
        page.bgcolor = saturn.Colors.SURFACE
        page.padding = 24
        page.spacing = 16

        state = {"n": 0}

        def log(msg):
            out.value = msg
            out.update()

        def on_click(e):
            state["n"] += 1
            log(f"last event: click #{state['n']}")

        out = saturn.Text("interact with the controls below", size=13,
                      color=saturn.Colors.ON_SURFACE_VARIANT)

        name = saturn.TextField(label="Name", on_change=lambda e: log(f"name={e.data!r}"),
                            on_submit=lambda e: log(f"submitted {e.data!r}"))

        def Text_(i):
            return saturn.Text(f"list item {i}", size=13, color=saturn.Colors.ON_SURFACE)

        list_view = saturn.ListView(
            controls=[saturn.Container(Text_(i), padding=8,
                                   bgcolor=saturn.Colors.SURFACE_CONTAINER_LOW
                                   if i % 2 else saturn.Colors.SURFACE_CONTAINER,
                                   border_radius=6)
                      for i in range(30)],
            spacing=4, width=400, height=260, on_scroll=lambda e: None,
        )

        page.add(
            brand_header("Saturn Demo", detail=f"v{saturn.__version__}"),
            out,
            saturn.Row([
                demo_panel("Controls", [
                    saturn.Row([
                        saturn.Button("Elevated", icon=saturn.Icons.ADD, on_click=on_click),
                        saturn.FilledButton("Filled", on_click=on_click),
                        saturn.OutlinedButton("Outlined", on_click=on_click),
                        saturn.IconButton(saturn.Icons.FAVORITE, on_click=on_click),
                    ], spacing=8),
                    saturn.Row([
                        name,
                        saturn.Checkbox("agree", on_change=lambda e: log(f"agree={e.data}")),
                    ], spacing=12, vertical_alignment=saturn.CrossAxisAlignment.CENTER),
                    saturn.Row([
                        saturn.Slider(min=0, max=100, divisions=10,
                                  on_change=lambda e: log(f"slider={e.data}")),
                        saturn.Switch(on_change=lambda e: log(f"switch={e.data}")),
                        saturn.ProgressRing(0.6),
                    ], spacing=12),
                    saturn.Row([
                        saturn.Dropdown(hint_text="dropdown...",
                                    options=[saturn.Option(k, text=t) for k, t in
                                             (("a", "Alpha"), ("b", "Beta"), ("g", "Gamma"))],
                                    width=180,
                                    on_select=lambda e: log(f"select={e.data}")),
                        saturn.Image("examples/assets/test_img.png", width=140, height=70,
                                 border_radius=8),
                    ], spacing=12),
                    saturn.Row([
                        saturn.Button("Dialog", on_click=lambda e: page.show_dialog(
                            saturn.AlertDialog(title="Confirm",
                                           content=saturn.Text("Delete this item permanently?"),
                                           actions=[
                                               saturn.TextButton("Cancel", on_click=lambda e2: page.pop_dialog()),
                                               saturn.FilledButton("Delete", on_click=lambda e2: page.pop_dialog()),
                                           ]))),
                        saturn.Button("SnackBar", on_click=lambda e: page.show_dialog(
                            saturn.SnackBar("Saved!", action="Undo", duration=3000))),
                    ], spacing=8),
                ]),
                demo_panel("Scrollable list", [list_view]),
            ], spacing=24),
        )
        page.update()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=12342)
    parser.add_argument('--backend', choices=('opengl','vulkan','software'))
    args = parser.parse_args()
    if args.backend:
        backend = {'opengl':saturn.Renderer.OPENGL, 'vulkan':saturn.Renderer.VULKAN,
                   'software':saturn.Renderer.SOFTWARE}[args.backend]
        saturn.run(main=Application().create_window,backend=backend)
    else:
        import errno
        import socket
        import uvicorn
        with socket.socket() as listener:
            try:
                listener.bind(('127.0.0.1',args.port))
            except OSError as error:
                if error.errno != errno.EADDRINUSE and getattr(error,'winerror',None) != 10048:
                    raise
                listener.bind(('127.0.0.1',0))
                print(f'Port {args.port} is already in use; using an available port.',flush=True)
            port=listener.getsockname()[1]
            listener.listen(2048)
            print(f'Saturn demo: http://127.0.0.1:{port}/',flush=True)
            config=uvicorn.Config(saturn.web.create_app(Application().create_window),
                                  host='127.0.0.1',port=port)
            uvicorn.Server(config).run(sockets=[listener])
