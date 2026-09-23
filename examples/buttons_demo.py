import saturn
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header, demo_panel

state = {"n": 0}


class Application:
    def create_window(self, page: saturn.Page):
        page.title = "saturn buttons"
        page.theme_mode = saturn.ThemeMode.DARK
        page.bgcolor = saturn.Colors.SURFACE
        page.padding = 16
        page.spacing = 10

        def clicked(e):
            state["n"] += 1
            counter.value = f"clicked {state['n']} times"
            counter.color = saturn.Colors.ERROR if state["n"] > 2 else saturn.Colors.ON_SURFACE
            counter.update()

        def hovered(e):
            hover_label.value = f"hover: {e.data}"
            hover_label.update()

        counter = saturn.Text("clicked 0 times", size=16)
        hover_label = saturn.Text("hover: -", size=13,
                              color=saturn.Colors.ON_SURFACE_VARIANT)

        page.add(
            brand_header("Buttons Demo"),
            counter,
            hover_label,
            saturn.Row([
                demo_panel("Emphasis", [
                    saturn.ElevatedButton("Elevated", icon=saturn.Icons.ADD,
                                      on_click=clicked, on_hover=hovered),
                    saturn.FilledButton("Filled", on_click=clicked),
                    saturn.FilledTonalButton("Tonal", on_click=clicked),
                ]),
                demo_panel("Other actions", [
                    saturn.OutlinedButton("Outlined", on_click=clicked),
                    saturn.TextButton("Text", on_click=clicked),
                    saturn.Row([
                        saturn.IconButton(saturn.Icons.FAVORITE, on_click=clicked),
                        saturn.IconButton(saturn.Icons.DELETE, icon_color=saturn.Colors.ERROR,
                                      on_click=clicked),
                        saturn.ElevatedButton("Disabled", disabled=True),
                    ], spacing=8),
                    saturn.ElevatedButton("Long label button with icon",
                                      icon=saturn.Icons.SETTINGS,
                                      bgcolor=saturn.Colors.PRIMARY_CONTAINER,
                                      color=saturn.Colors.ON_PRIMARY_CONTAINER,
                                      on_click=clicked),
                ]),
            ], spacing=24),
        )
        page.update()


if __name__ == "__main__":
    saturn.run(main=Application().create_window, backend=saturn.Renderer.SOFTWARE,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
