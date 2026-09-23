import saturn as ft
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header


class Application:
    def create_window(self, page: ft.Page):
        page.title = "saturn hello"
        page.bgcolor = "#1c1b1f"
        page.padding = 24
        page.add(
            brand_header("Hello Demo"),
            ft.Text("Hello from saturn!", size=32, color="#e6e1e5"),
        )
        page.update()


if __name__ == "__main__":
    app = ft.run(main=Application().create_window, backend=ft.Render.SOFTWARE,
           width=DEMO_WIDTH, height=DEMO_HEIGHT)
    print("window closed, app returned:", type(app).__name__)
