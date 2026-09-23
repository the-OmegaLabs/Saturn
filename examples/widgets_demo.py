import saturn
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header, demo_panel

ICON = "examples/assets/test_icon.png"


class Application:
    def create_window(self, page: saturn.Page):
        page.title = "saturn widgets"
        page.theme_mode = saturn.ThemeMode.DARK
        page.bgcolor = saturn.Colors.SURFACE
        page.padding = 16
        page.spacing = 12

        page.add(
            brand_header("Widgets Demo"),
            saturn.Row([
                demo_panel("Icons and images", [
                    saturn.Row([
                        saturn.Icon(saturn.Icons.HOME, color=saturn.Colors.PRIMARY, size=28),
                        saturn.Icon(saturn.Icons.SETTINGS, color=saturn.Colors.ON_SURFACE_VARIANT),
                        saturn.Icon(saturn.Icons.ADD, color=saturn.Colors.PRIMARY, size=20),
                        saturn.Icon(saturn.Icons.SEARCH, color=saturn.Colors.ERROR, size=36),
                    ], spacing=16),
                    saturn.Row([
                        saturn.Image("examples/assets/test_img.png", width=120,
                                 height=70, border_radius=8),
                        saturn.Image("examples/assets/test_img.png", width=70,
                                 height=70, fit=saturn.BoxFit.CONTAIN),
                    ], spacing=12),
                    saturn.Card(saturn.Container(
                        saturn.Text("Card with content", color=saturn.Colors.ON_SURFACE),
                        padding=14,
                    )),
                ]),
                demo_panel("Progress", [
                    saturn.ProgressBar(0.7),
                    saturn.ProgressBar(),
                    saturn.Row([
                        saturn.ProgressRing(0.75),
                        saturn.ProgressRing(),
                        saturn.ProgressRing(value=0.5, color=saturn.Colors.ERROR),
                    ], spacing=16),
                ]),
            ], spacing=24),
        )
        page.update()


if __name__ == "__main__":
    saturn.run(main=Application().create_window, backend=saturn.Renderer.VULKAN,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
