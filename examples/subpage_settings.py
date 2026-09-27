"""Owned native settings windows and a shared application route.

python examples/subpage_settings.py --backend vulkan --screen settings
"""
import saturn as st
if __package__:
    from .effects_demo_common import configure, heading, caption, panel, primary, run_example, BACKGROUND
else:
    from effects_demo_common import configure, heading, caption, panel, primary, run_example, BACKGROUND


def build(page):
    configure(page, "Saturn · Native settings")
    state = {"name": "Orbital Studio", "notifications": True}
    windows = {}
    title = st.Text(state["name"], size=28)
    route_label = caption("Route: /")

    def preferences(child):
        child.window.width, child.window.height = 420, 430
        child.bgcolor = BACKGROUND
        child.padding = 20
        child.horizontal_alignment = st.CrossAxisAlignment.STRETCH
        def change_name(e):
            state["name"] = e.control.value
            title.value = state["name"]
            page.update()
        def change_notifications(e):
            state["notifications"] = e.control.value
        child.add(st.Text("Preferences", size=24),
                  st.TextField(state["name"], label="Workspace name", on_change=change_name),
                  st.Switch(label="Notifications", value=state["notifications"], on_change=change_notifications),
                  st.OutlinedButton("Open appearance window", on_click=lambda e: child.go("/settings/appearance")),
                  st.Row(st.TextButton("Hide", on_click=lambda e: child.hide()),
                         st.FilledButton("Close", on_click=lambda e: child.close())))

    def appearance(child):
        child.window.width, child.window.height = 360, 330
        child.bgcolor = BACKGROUND
        child.padding = 20
        child.add(st.Text("Appearance", size=24),
                  st.Shader(shader=st.ShaderEffect.PLASMA, width=300, height=180, border_radius=20),
                  st.TextButton("Close", on_click=lambda e: child.close()))

    def open_window(name):
        child = windows.get(name)
        if child is None or child.closed:
            owner = windows.get("settings") if name == "appearance" else page
            if owner is None or getattr(owner, "closed", False):
                open_window("settings")
                owner = windows["settings"]
            child = owner.open_subpage(preferences if name == "settings" else appearance,
                                      title=name.title(), anchor="center" if name == "settings" else "right",
                                      offset=(12, 0) if name == "appearance" else None)
            windows[name] = child
        else:
            child.show()
            child.to_front()
        return child

    def route_changed(e):
        route_label.value = f"Route: {e.route}"
        if e.route == "/settings":
            open_window("settings")
        elif e.route == "/settings/appearance":
            open_window("appearance")
        page.update()
    page.on_route_change = route_changed

    def open_screen(name):
        # Explicitly open even if the route already has this value.
        open_window(name)
        page.go("/settings/appearance" if name == "appearance" else "/settings")

    page.add(heading(page, "Native child windows", "Subpage / Toplevel"),
             panel(title, caption("Settings open in a separate owned window."),
                   primary("Open preferences", lambda e: open_screen("settings"))),
             route_label,
             st.Row(st.OutlinedButton("Show settings", on_click=lambda e: open_window("settings")),
                    st.OutlinedButton("Attach on the right", on_click=lambda e:
                        open_window("settings").attach("right", offset=(12, 0), follow_parent=True))),
             caption("Close a child to keep working here. Closing this window closes its children."))
    return {"state": state, "windows": windows, "open_screen": open_screen}


if __name__ == "__main__":
    run_example(build, "Owned native settings windows", ("home", "settings", "appearance"))
