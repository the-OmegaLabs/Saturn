import saturn as ft
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header, demo_panel

ICON = "examples/assets/test_icon.png"


class Application:
    def create_window(self, page: ft.Page):
        page.title = "saturn widgets"
        page.bgcolor = ft.Colors.SURFACE
        page.padding = 16
        page.spacing = 12

        page.add(
            brand_header("Widgets Demo"),
            ft.Row([
                demo_panel("Icons and images", [
                    ft.Row([
                        ft.Icon(ft.Icons.HOME, color=ft.Colors.PRIMARY, size=28),
                        ft.Icon(ft.Icons.SETTINGS, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Icon(ft.Icons.ADD, color=ft.Colors.PRIMARY, size=20),
                        ft.Icon(ft.Icons.SEARCH, color=ft.Colors.ERROR, size=36),
                    ], spacing=16),
                    ft.Row([
                        ft.Image("examples/assets/test_img.png", width=120,
                                 height=70, border_radius=8),
                        ft.Image("examples/assets/test_img.png", width=70,
                                 height=70, fit=ft.BoxFit.CONTAIN),
                    ], spacing=12),
                    ft.Card(ft.Container(
                        ft.Text("Card with content", color=ft.Colors.ON_SURFACE),
                        padding=14,
                    )),
                ]),
                demo_panel("Progress", [
                    ft.ProgressBar(0.7),
                    ft.ProgressBar(),
                    ft.Row([
                        ft.ProgressRing(0.75),
                        ft.ProgressRing(),
                        ft.ProgressRing(value=0.5, color=ft.Colors.ERROR),
                    ], spacing=16),
                ]),
            ], spacing=24),
        )
        page.update()


if __name__ == "__main__":
    ft.run(main=Application().create_window, backend=ft.Render.SOFTWARE,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
