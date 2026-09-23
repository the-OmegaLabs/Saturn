import saturn as ft
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header


class Application:
    def create_window(self, page: ft.Page):
        page.title = "saturn layout"
        page.bgcolor = ft.Colors.SURFACE
        page.padding = 16
        page.spacing = 12

        box = lambda txt, color, **kw: ft.Container(
            ft.Text(txt, size=15, color=ft.Colors.ON_PRIMARY),
            bgcolor=color, padding=12, border_radius=8,
            alignment=ft.Alignment.CENTER, **kw,
        )

        page.add(
            brand_header("Layout Demo"),
            ft.Text("Layout engine demo", size=22, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.PRIMARY),
            ft.Row(
                box("expand 1", ft.Colors.INDIGO_400, expand=1),
                box("expand 2", ft.Colors.TEAL_400, expand=1),
                box("expand 3", ft.Colors.PINK_400, expand=1),
                spacing=8,
            ),
            ft.Container(
                ft.Row(
                    box("A", ft.Colors.BLUE_400),
                    box("B", ft.Colors.BLUE_400),
                    box("C", ft.Colors.BLUE_400),
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                padding=10, border_radius=12,
                border=ft.Border.all(1, ft.Colors.OUTLINE),
            ),
            ft.Row(
                ft.Container(
                    ft.Column(
                        ft.Text("card title", weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ON_SURFACE),
                        ft.Text("subtitle wrapped inside a fixed width card "
                                "to exercise wrapping", size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT),
                        spacing=4,
                    ),
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    padding=12, border_radius=10, width=180,
                ),
                ft.Container(
                    ft.Stack(
                        ft.Container(bgcolor=ft.Colors.PRIMARY,
                                     width=120, height=80, border_radius=10),
                        ft.Text("stacked", size=12, color=ft.Colors.ON_PRIMARY,
                                left=12, top=12),
                    ),
                    alignment=ft.Alignment.CENTER,
                ),
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            ft.Container(
                ft.Text("dark container, centered text",
                        color=ft.Colors.ON_PRIMARY_CONTAINER),
                bgcolor=ft.Colors.PRIMARY_CONTAINER, padding=14,
                border_radius=10, alignment=ft.Alignment.CENTER,
            ),
            ft.Divider(),
            ft.Row(
                box("start", ft.Colors.DEEP_PURPLE_300),
                box("end", ft.Colors.DEEP_PURPLE_300),
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=8,
            ),
        )
        page.update()


if __name__ == "__main__":
    ft.run(main=Application().create_window, backend=ft.Render.SOFTWARE,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
