import saturn as ft
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header, demo_panel

state = {"n": 0}


class Application:
    def create_window(self, page: ft.Page):
        page.title = "saturn buttons"
        page.bgcolor = ft.Colors.SURFACE
        page.padding = 16
        page.spacing = 10

        def clicked(e):
            state["n"] += 1
            counter.value = f"clicked {state['n']} times"
            counter.color = ft.Colors.ERROR if state["n"] > 2 else ft.Colors.ON_SURFACE
            counter.update()

        def hovered(e):
            hover_label.value = f"hover: {e.data}"
            hover_label.update()

        counter = ft.Text("clicked 0 times", size=16)
        hover_label = ft.Text("hover: -", size=13,
                              color=ft.Colors.ON_SURFACE_VARIANT)

        page.add(
            brand_header("Buttons Demo"),
            counter,
            hover_label,
            ft.Row([
                demo_panel("Emphasis", [
                    ft.ElevatedButton("Elevated", icon=ft.Icons.ADD,
                                      on_click=clicked, on_hover=hovered),
                    ft.FilledButton("Filled", on_click=clicked),
                    ft.FilledTonalButton("Tonal", on_click=clicked),
                ]),
                demo_panel("Other actions", [
                    ft.OutlinedButton("Outlined", on_click=clicked),
                    ft.TextButton("Text", on_click=clicked),
                    ft.Row([
                        ft.IconButton(ft.Icons.FAVORITE, on_click=clicked),
                        ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.ERROR,
                                      on_click=clicked),
                        ft.ElevatedButton("Disabled", disabled=True),
                    ], spacing=8),
                    ft.ElevatedButton("Long label button with icon",
                                      icon=ft.Icons.SETTINGS,
                                      bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                      color=ft.Colors.ON_PRIMARY_CONTAINER,
                                      on_click=clicked),
                ]),
            ], spacing=24),
        )
        page.update()


if __name__ == "__main__":
    ft.run(main=Application().create_window, backend=ft.Render.SOFTWARE,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
