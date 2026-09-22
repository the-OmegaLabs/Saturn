import saturn as ft


class Application:
    def create_window(self, page: ft.Page):
        page.title = "saturn hello"
        page.bgcolor = "#1c1b1f"
        page.add(ft.Text("Hello from saturn!", size=32, color="#e6e1e5"))
        page.update()


s = Application()
app = ft.run(main=s.create_window, backend=ft.Render.SOFTWARE)
print("window closed, app returned:", type(app).__name__)
