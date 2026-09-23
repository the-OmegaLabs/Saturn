import saturn
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header


class Application:
    def create_window(self, page: saturn.Page):
        page.title = "saturn layout"
        page.theme_mode = saturn.ThemeMode.DARK
        page.bgcolor = saturn.Colors.SURFACE
        page.padding = 16
        page.spacing = 12

        box = lambda txt, color, **kw: saturn.Container(
            saturn.Text(txt, size=15, color=saturn.Colors.ON_PRIMARY),
            bgcolor=color, padding=12, border_radius=8,
            alignment=saturn.Alignment.CENTER, **kw,
        )

        page.add(
            brand_header("Layout Demo"),
            saturn.Text("Layout engine demo", size=22, weight=saturn.FontWeight.BOLD,
                    color=saturn.Colors.PRIMARY),
            saturn.Row(
                box("expand 1", saturn.Colors.INDIGO_400, expand=1),
                box("expand 2", saturn.Colors.TEAL_400, expand=1),
                box("expand 3", saturn.Colors.PINK_400, expand=1),
                spacing=8,
            ),
            saturn.Container(
                saturn.Row(
                    box("A", saturn.Colors.BLUE_400),
                    box("B", saturn.Colors.BLUE_400),
                    box("C", saturn.Colors.BLUE_400),
                    alignment=saturn.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=saturn.CrossAxisAlignment.CENTER,
                ),
                bgcolor=saturn.Colors.SURFACE_CONTAINER_HIGHEST,
                padding=10, border_radius=12,
                border=saturn.Border.all(1, saturn.Colors.OUTLINE),
            ),
            saturn.Row(
                saturn.Container(
                    saturn.Column(
                        saturn.Text("card title", weight=saturn.FontWeight.BOLD,
                                color=saturn.Colors.ON_SURFACE),
                        saturn.Text("subtitle wrapped inside a fixed width card "
                                "to exercise wrapping", size=12,
                                color=saturn.Colors.ON_SURFACE_VARIANT),
                        spacing=4,
                    ),
                    bgcolor=saturn.Colors.SURFACE_CONTAINER_LOW,
                    padding=12, border_radius=10, width=180,
                ),
                saturn.Container(
                    saturn.Stack(
                        saturn.Container(bgcolor=saturn.Colors.PRIMARY,
                                     width=120, height=80, border_radius=10),
                        saturn.Text("stacked", size=12, color=saturn.Colors.ON_PRIMARY,
                                left=12, top=12),
                    ),
                    alignment=saturn.Alignment.CENTER,
                ),
                vertical_alignment=saturn.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            saturn.Container(
                saturn.Text("dark container, centered text",
                        color=saturn.Colors.ON_PRIMARY_CONTAINER),
                bgcolor=saturn.Colors.PRIMARY_CONTAINER, padding=14,
                border_radius=10, alignment=saturn.Alignment.CENTER,
            ),
            saturn.Divider(),
            saturn.Row(
                box("start", saturn.Colors.DEEP_PURPLE_300),
                box("end", saturn.Colors.DEEP_PURPLE_300),
                alignment=saturn.MainAxisAlignment.SPACE_BETWEEN, spacing=8,
            ),
        )
        page.update()


if __name__ == "__main__":
    saturn.run(main=Application().create_window, backend=saturn.Render.SOFTWARE,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
