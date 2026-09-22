import saturn as ft


class Application:
    def create_window(self, page: ft.Page):
        page.title = "saturn inputs"
        page.bgcolor = ft.Colors.SURFACE
        page.padding = 16
        page.spacing = 10

        def log(msg):
            label.value = msg
            label.update()

        label = ft.Text("interact below", size=13,
                        color=ft.Colors.ON_SURFACE_VARIANT)
        name = ft.TextField(label="Name", hint_text="type here",
                            on_change=lambda e: log(f"name = {e.data!r}"),
                            on_submit=lambda e: log(f"submitted {e.data!r}"))
        pwd = ft.TextField(label="Password", password=True, width=240)
        cb = ft.Checkbox("I agree", on_change=lambda e: log(f"agree = {e.data}"))
        sw = ft.Switch("Dark", on_change=lambda e: log(f"dark = {e.data}"))

        def on_mode(e):
            log(f"mode = {e.data}")

        grp = ft.RadioGroup(on_change=on_mode,
                            content=ft.Row(
                                ft.Radio("pdf", label="PDF"),
                                ft.Radio("csv", label="CSV"), spacing=6))
        slider = ft.Slider(min=0, max=100, divisions=10,
                           on_change=lambda e: log(f"slider = {e.data}"))
        dd = ft.Dropdown(
            hint_text="choose...",
            options=[ft.dropdown.Option("a", text="Alpha"),
                     ft.dropdown.Option("b", text="Beta"),
                     ft.dropdown.Option("g", text="Gamma")],
            on_select=lambda e: log(f"picked = {e.data}"))

        page.add(label, name, pwd, cb, sw, grp, slider, dd)
        page.update()


s = Application()
app = ft.run(main=s.create_window, backend=ft.Render.SOFTWARE, width=460, height=460)
