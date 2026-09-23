import saturn
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header, demo_panel


class Application:
    def create_window(self, page: saturn.Page):
        page.title = "saturn text"
        page.theme_mode = saturn.ThemeMode.DARK
        page.bgcolor = saturn.Colors.SURFACE
        page.add(
            brand_header("Text Demo"),
            saturn.Row([
                demo_panel("Type scale and wrapping", [
                    saturn.Text("Short line, 32px, bold", size=32,
                            weight=saturn.FontWeight.BOLD, color=saturn.Colors.PRIMARY),
                    saturn.Text("Wrapped: " + "saturn flex text layout " * 12,
                            size=14, color=saturn.Colors.ON_SURFACE),
                ]),
                demo_panel("Overflow and alignment", [
                    saturn.Text("Max 2 lines with ellipsis: " +
                            "lorem ipsum dolor sit amet " * 10,
                            size=14, max_lines=2,
                            color=saturn.Colors.ON_SURFACE_VARIANT),
                    saturn.Text("Right aligned", size=16,
                            text_align=saturn.TextAlign.RIGHT,
                            color=saturn.Colors.ON_SURFACE),
                    saturn.Text("center", size=16,
                            text_align=saturn.TextAlign.CENTER,
                            color=saturn.Colors.ON_SURFACE),
                ]),
            ], spacing=24),
        )
        page.update()


if __name__ == "__main__":
    saturn.run(main=Application().create_window, backend=saturn.Renderer.SOFTWARE,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
