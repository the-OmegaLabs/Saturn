"""Four portable procedural backgrounds in a compact live gallery.

python examples/shader_gallery.py --backend vulkan
"""
from __future__ import annotations

import saturn as st

if __package__:
    from .effects_demo_common import (ACCENT, INK, caption, configure, heading,
        palette_options, panel, renderer_note, run_example, shader_palette)
else:
    from effects_demo_common import (ACCENT, INK, caption, configure, heading,
        palette_options, panel, renderer_note, run_example, shader_palette)


def build(page: st.Page):
    configure(page, "Saturn · Shader gallery")
    descriptions = {"gradient": "Slowly turn a smooth color field.",
                    "noise": "Layer soft procedural texture.",
                    "ripple": "Send rings through a color field.",
                    "plasma": "Blend overlapping waves into flowing color."}
    shaders = []
    cards = []
    state = {"palette": "aurora", "animate": True}
    for effect in st.ShaderEffect:
        shader = st.Shader(effect, height=104, speed=.7, border_radius=12,
                           uniforms={"frequency": 4}, key=f"gallery.{effect.value}")
        shader_palette(shader, state["palette"])
        shaders.append(shader)
        card = st.Container(
            st.Column(shader,
                      st.Row(st.Text(effect.value.title(), size=16, color=INK, expand=True),
                             st.Text(f"0{len(cards)+1}", size=11, color=ACCENT), height=22),
                      caption(descriptions[effect.value], size=12), spacing=8, tight=True,
                      horizontal_alignment=st.CrossAxisAlignment.STRETCH),
            width=350, expand=True, height=180, padding=12,
            bgcolor="#1A2230", border_radius=22,
        )
        cards.append(card)

    status = caption("Four effects. One palette. A shared animation clock.", size=12)

    def change_motion(event):
        state["animate"] = bool(event.control.value)
        for shader in shaders:
            shader.animate = state["animate"]
        status.value = "Animation is running." if state["animate"] else "Animation is paused. Colors and clipping remain active."
        page.update()

    def change_palette(event):
        state["palette"] = event.control.value
        for shader in shaders:
            shader_palette(shader, state["palette"])
        page.update()

    motion = st.Switch("Animate all", value=True, on_change=change_motion,
                       width=180, key="gallery.motion")
    palette = st.Dropdown(value=state["palette"], options=palette_options(),
                          hint_text="Palette", on_select=change_palette, width=240,
                          key="gallery.palette")

    def reset(event=None):
        state.update(palette="aurora", animate=True)
        palette.value, motion.value = "aurora", True
        for shader in shaders:
            shader_palette(shader, "aurora")
            shader.animate, shader.speed, shader.time = True, .7, 0
            shader.uniforms = {"frequency": 4}
        status.value = "Four effects. One palette. A shared animation clock."
        page.update()

    page.add(
        heading(page, "Procedural backgrounds", "Shader / live gallery"),
        caption("Explore four portable effects. Pause motion or switch the palette for all previews."),
        st.Row(motion, caption("Palette"), palette,
               st.OutlinedButton("Reset", on_click=reset, key="gallery.reset"),
               height=56, spacing=16),
        st.Row(cards[0], cards[1], spacing=16, height=180),
        st.Row(cards[2], cards[3], spacing=16, height=180),
        status, caption(renderer_note(page), size=12),
    )
    page.update()
    return {"shaders": shaders, "motion": motion, "palette": palette,
            "state": state, "reset": reset, "status": status,
            "open_screen": lambda screen: None}


if __name__ == "__main__":
    run_example(build, "Portable Shader gallery")
