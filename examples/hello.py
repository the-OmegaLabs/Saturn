import saturn
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header


class Application:
    def create_window(self, page: saturn.Page):
        page.title = "saturn hello"
        page.theme_mode = saturn.ThemeMode.DARK
        page.bgcolor = "#1c1b1f"
        page.padding = 24
        page.add(
            brand_header("Hello Demo"),
            saturn.Text("Hello from saturn!", size=32, color="#e6e1e5"),
        )
        page.update()


if __name__ == "__main__":
    saturn.run(main=Application().create_window, backend=saturn.Renderer.OPENGL,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
