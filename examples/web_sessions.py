"""Run this file, then open two /?room=demo tabs or isolated / tabs."""
import saturn as st
from saturn.web import create_app


def main(page):
    room = page.web.query.get("room")
    if room:
        page.web.session = room
    if not page.web.is_new_session:
        return
    page.title = "Saturn Web sessions"
    page.padding = 24
    page.spacing = 12
    counter = st.Text("Count: 0", size=24, weight=st.FontWeight.BOLD)
    clients = st.Text("Connected views: 0")
    notice = st.Text("No named messages yet")
    route = st.Text("Route: /")
    echo = st.Text("Accepted text: ")
    field = st.TextField(label="Shared text · native caret and IME", width=440)
    fade = st.Container(st.Text("Opacity runs locally in each browser"),
                        bgcolor="surfacecontainerhighest", padding=16, height=54,
                        width=440, animate_opacity=250)
    count = 0

    def increment(e):
        nonlocal count
        count += 1
        counter.value = f"Count: {count}"
        page.update()

    def changed(e):
        echo.value = f"Accepted text: {e.data}"
        page.update()

    def connections(e):
        clients.value = f"Connected views: {page.web.connection_count}"
        page.update()

    def message(e):
        notice.value = f"Named message #{e.sequence}: {e.data}"
        page.update()

    def fade_toggle(e):
        fade.opacity = .2 if fade._raw('opacity') == 1 else 1
        page.update()

    def route_changed(e):
        route.value = f"Route: {page.route}"
        page.update()

    page.web.on_connect = page.web.on_disconnect = connections
    page.web.events.subscribe("notice", message)
    field.on_change = changed
    page.on_route_change = route_changed
    page.add(
        st.Text("Saturn Web", size=32, weight=st.FontWeight.BOLD),
        st.Text(f"Session: {page.web.session}"), clients,
        st.Row(counter, st.FilledButton("Increment", on_click=increment), spacing=24),
        field, echo,
        st.Checkbox("Shared checkbox"),
        st.Row(st.OutlinedButton("Send named message", on_click=lambda e:
                   page.web.events.send("notice", {"count": count})),
               st.TextButton("Settings route", on_click=lambda e: page.go("/settings"))),
        notice, route, fade, st.TextButton("Animate opacity", on_click=fade_toggle),
        st.ListView(controls=[st.Text(f"Row {i:03d} · scroll stays in this view", height=32)
                             for i in range(500)], height=180, width=440, item_extent=32),
    )


app = create_app(main)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
