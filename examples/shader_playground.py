"""Edit a live shader from an independent native settings window."""
import saturn as st
if __package__:
    from .effects_demo_common import configure, heading, caption, primary, run_example, BACKGROUND
else:
    from effects_demo_common import configure, heading, caption, primary, run_example, BACKGROUND


def build(page):
    configure(page, "Saturn · Shader playground")
    preview = st.Shader(shader=st.ShaderEffect.PLASMA, height=380, border_radius=24)
    windows = {}
    def editor(child):
        child.window.width, child.window.height = 440, 490
        child.bgcolor = BACKGROUND
        child.padding = 20
        child.horizontal_alignment = st.CrossAxisAlignment.STRETCH
        def effect_changed(e):
            preview.shader = st.ShaderEffect(e.control.value)
            preview.uniforms = {}
            preview.update()
        def speed_changed(e):
            preview.speed = float(e.control.value)
            preview.update()
        def intensity_changed(e):
            preview.uniforms["intensity"] = float(e.control.value)
            preview.update()
        child.add(st.Text("Live shader settings", size=24),
                  st.Dropdown(value=preview.effect, options=[st.DropdownOption(key=x.value, text=x.name.title())
                              for x in st.ShaderEffect], on_select=effect_changed),
                  caption("Speed"), st.Slider(value=preview.speed, min=0, max=3, on_change=speed_changed),
                  caption("Intensity"), st.Slider(value=1, min=0, max=1, on_change=intensity_changed),
                  st.Switch(label="Animate", value=True, on_change=lambda e: set_motion(e.control.value)),
                  st.FilledButton("Close", on_click=lambda e: child.close()))
    def set_motion(value):
        preview.animate = bool(value)
        preview.update()
    def open_screen(name="editor"):
        child = windows.get("editor")
        if child is None or child.closed:
            child = page.open_subpage(editor, title="Shader settings", anchor="right", offset=(12, 0))
            windows["editor"] = child
        else:
            child.show()
            child.to_front()
        return child
    page.add(heading(page, "Procedural shader", "Live GPU preview"), preview,
             primary("Open shader settings", lambda e: open_screen()),
             caption("The separate settings window updates this preview immediately."))
    return {"preview": preview, "windows": windows, "open_screen": open_screen}


if __name__ == "__main__":
    run_example(build, "Shader with a native settings window", ("home", "editor"))
