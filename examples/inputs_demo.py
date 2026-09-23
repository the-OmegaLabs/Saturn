import saturn
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header, demo_panel


class Application:
    def create_window(self, page: saturn.Page):
        page.title = "saturn inputs"
        page.theme_mode = saturn.ThemeMode.DARK
        page.bgcolor = saturn.Colors.SURFACE
        page.padding = 16
        page.spacing = 10

        def log(msg):
            label.value = msg
            label.update()

        label = saturn.Text("interact below", size=13,
                        color=saturn.Colors.ON_SURFACE_VARIANT)
        name = saturn.TextField(label="Name", hint_text="type here",
                            on_change=lambda e: log(f"name = {e.data!r}"),
                            on_submit=lambda e: log(f"submitted {e.data!r}"))
        pwd = saturn.TextField(label="Password", password=True, width=240)
        cb = saturn.Checkbox("I agree", on_change=lambda e: log(f"agree = {e.data}"))
        sw = saturn.Switch("Dark", on_change=lambda e: log(f"dark = {e.data}"))

        def on_mode(e):
            log(f"mode = {e.data}")

        grp = saturn.RadioGroup(on_change=on_mode,
                            content=saturn.Row(
                                saturn.Radio("pdf", label="PDF"),
                                saturn.Radio("csv", label="CSV"), spacing=6))
        slider = saturn.Slider(min=0, max=100, divisions=10,
                           on_change=lambda e: log(f"slider = {e.data}"))
        dd = saturn.Dropdown(
            hint_text="choose...",
            options=[saturn.Option("a", text="Alpha"),
                     saturn.Option("b", text="Beta"),
                     saturn.Option("g", text="Gamma")],
            on_select=lambda e: log(f"picked = {e.data}"))

        page.add(
            brand_header("Inputs Demo"),
            label,
            saturn.Row([
                demo_panel("Text and selection", [name, pwd, dd]),
                demo_panel("Choices and range", [cb, sw, grp, slider]),
            ], spacing=24),
        )
        page.update()


if __name__ == "__main__":
    saturn.run(main=Application().create_window, backend=saturn.Render.SOFTWARE,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
