import saturn as ft
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header, demo_panel


class Application:
    def create_window(self, page: ft.Page):
        page.title = "saturn text"
        page.bgcolor = ft.Colors.SURFACE
        page.add(
            brand_header("Text Demo"),
            ft.Row([
                demo_panel("Type scale and wrapping", [
                    ft.Text("Short line, 32px, bold", size=32,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                    ft.Text("Wrapped: " + "saturn flex text layout " * 12,
                            size=14, color=ft.Colors.ON_SURFACE),
                ]),
                demo_panel("Overflow and alignment", [
                    ft.Text("Max 2 lines with ellipsis: " +
                            "lorem ipsum dolor sit amet " * 10,
                            size=14, max_lines=2,
                            color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("Right aligned", size=16,
                            text_align=ft.TextAlign.RIGHT,
                            color=ft.Colors.ON_SURFACE),
                    ft.Text("center", size=16,
                            text_align=ft.TextAlign.CENTER,
                            color=ft.Colors.ON_SURFACE),
                ]),
            ], spacing=24),
        )
        page.update()


if __name__ == "__main__":
    ft.run(main=Application().create_window, backend=ft.Render.SOFTWARE,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
