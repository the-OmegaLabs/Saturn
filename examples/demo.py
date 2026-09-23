"""saturn 全功能汇总 demo — 核心集控件一次看全。

跑法:
    .venv/Scripts/python.exe examples/demo.py                     # SOFTWARE
    .venv/Scripts/python.exe examples/demo.py --backend opengl    # OPENGL
"""
import sys

import saturn as ft
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header, demo_panel


class Application:
    def create_window(self, page: ft.Page):
        page.title = "saturn demo"
        page.bgcolor = ft.Colors.SURFACE
        page.padding = 24
        page.spacing = 16

        state = {"n": 0}

        def log(msg):
            out.value = msg
            out.update()

        def on_click(e):
            state["n"] += 1
            log(f"last event: click #{state['n']}")

        out = ft.Text("interact with the controls below", size=13,
                      color=ft.Colors.ON_SURFACE_VARIANT)

        name = ft.TextField(label="Name", on_change=lambda e: log(f"name={e.data!r}"),
                            on_submit=lambda e: log(f"submitted {e.data!r}"))

        def Text_(i):
            return ft.Text(f"list item {i}", size=13, color=ft.Colors.ON_SURFACE)

        list_view = ft.ListView(
            controls=[ft.Container(Text_(i), padding=8,
                                   bgcolor=ft.Colors.SURFACE_CONTAINER_LOW
                                   if i % 2 else ft.Colors.SURFACE_CONTAINER,
                                   border_radius=6)
                      for i in range(30)],
            spacing=4, width=400, height=260, on_scroll=lambda e: None,
        )

        page.add(
            brand_header("Saturn Demo", detail=f"v{ft.__version__}"),
            out,
            ft.Row([
                demo_panel("Controls", [
                    ft.Row([
                        ft.Button("Elevated", icon=ft.Icons.ADD, on_click=on_click),
                        ft.FilledButton("Filled", on_click=on_click),
                        ft.OutlinedButton("Outlined", on_click=on_click),
                        ft.IconButton(ft.Icons.FAVORITE, on_click=on_click),
                    ], spacing=8),
                    ft.Row([
                        name,
                        ft.Checkbox("agree", on_change=lambda e: log(f"agree={e.data}")),
                    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        ft.Slider(min=0, max=100, divisions=10,
                                  on_change=lambda e: log(f"slider={e.data}")),
                        ft.Switch(on_change=lambda e: log(f"switch={e.data}")),
                        ft.ProgressRing(0.6),
                    ], spacing=12),
                    ft.Row([
                        ft.Dropdown(hint_text="dropdown...",
                                    options=[ft.dropdown.Option(k, text=t) for k, t in
                                             (("a", "Alpha"), ("b", "Beta"), ("g", "Gamma"))],
                                    width=180,
                                    on_select=lambda e: log(f"select={e.data}")),
                        ft.Image("examples/assets/test_img.png", width=140, height=70,
                                 border_radius=8),
                    ], spacing=12),
                    ft.Row([
                        ft.Button("Dialog", on_click=lambda e: page.show_dialog(
                            ft.AlertDialog(title="Confirm",
                                           content=ft.Text("Delete this item permanently?"),
                                           actions=[
                                               ft.TextButton("Cancel", on_click=lambda e2: page.pop_dialog()),
                                               ft.FilledButton("Delete", on_click=lambda e2: page.pop_dialog()),
                                           ]))),
                        ft.Button("SnackBar", on_click=lambda e: page.show_dialog(
                            ft.SnackBar("Saved!", action="Undo", duration=3000))),
                    ], spacing=8),
                ]),
                demo_panel("Scrollable list", [list_view]),
            ], spacing=24),
        )
        page.update()


if __name__ == "__main__":
    backend = ft.Render.OPENGL if "--backend" in sys.argv and "opengl" in sys.argv \
        else ft.Render.SOFTWARE
    app = ft.run(main=Application().create_window, backend=backend,
                 width=DEMO_WIDTH, height=DEMO_HEIGHT)
