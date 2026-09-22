import saturn as ft


class Application:
    def create_window(self, page: ft.Page):
        page.title = "saturn text"
        page.bgcolor = ft.Colors.SURFACE
        page.add(
            ft.Text("Short line, 32px, bold", size=32,
                    weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
            ft.Text("Wrapped: " + "saturn flex text layout " * 12, size=14,
                    color=ft.Colors.ON_SURFACE),
            ft.Text("Max 2 lines with ellipsis: " + "lorem ipsum dolor sit amet " * 10,
                    size=14, max_lines=2, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Text("Right aligned", size=16, text_align=ft.TextAlign.RIGHT,
                    color=ft.Colors.ON_SURFACE),
            ft.Text("center", size=16, text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.ON_SURFACE),
        )
        page.update()


s = Application()
app = ft.run(main=s.create_window, backend=ft.Render.SOFTWARE, width=500, height=300)
