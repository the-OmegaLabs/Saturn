"""Presentation and command-line helpers for the Subpage and Shader examples."""
from __future__ import annotations

import argparse

import saturn as st


BACKGROUND = "#10141D"
PANEL = "#1A2230"
INK = "#F1F4FA"
MUTED = "#AAB6CA"
ACCENT = "#8EE2D0"
PALETTES = {
    "aurora": ("Aurora", "#164754", "#80E1CD"),
    "violet": ("Violet", "#392554", "#C8A9FF"),
    "sunset": ("Sunset", "#732D4C", "#FFB779"),
}


def configure(page: st.Page, title: str):
    page.title = title
    page.window.width, page.window.height = 900, 680
    page.window.min_width, page.window.min_height = 780, 580
    page.theme_mode = st.ThemeMode.DARK
    page.bgcolor = BACKGROUND
    page.padding = 20
    page.spacing = 12
    page.horizontal_alignment = st.CrossAxisAlignment.STRETCH


def backend_name(page):
    name = type(page.renderer.context).__name__
    return {"GLRenderer": "OPENGL", "VulkanRenderer": "VULKAN",
            "SoftwareRenderer": "SOFTWARE"}.get(name, name.upper())


def caption(value, *, size=13):
    return st.Text(value, size=size, color=MUTED)


def heading(page, title, tag):
    return st.Row(
        st.Column(st.Text(tag.upper(), size=11, color=ACCENT),
                  st.Text(title, size=28, weight=st.FontWeight.W_600, color=INK),
                  spacing=2, tight=True, expand=True),
        st.Container(st.Text(backend_name(page), size=11, color=ACCENT),
                     padding=10, bgcolor="#243B42", border_radius=12),
        height=56, spacing=16,
    )


def panel(*controls, height=None, width=None, expand=None, padding=16):
    return st.Container(
        st.Column(controls=list(controls), spacing=10, tight=True,
                  horizontal_alignment=st.CrossAxisAlignment.STRETCH),
        bgcolor=PANEL, border_radius=20, padding=padding,
        height=height, width=width, expand=expand,
    )


def primary(label, handler, *, key=None):
    return st.FilledButton(label, bgcolor=ACCENT, color="#102A25",
                           on_click=handler, key=key)


def palette_options():
    return [st.DropdownOption(key=key, text=value[0]) for key, value in PALETTES.items()]


def shader_palette(shader, name):
    _, shader.color, shader.secondary_color = PALETTES[name]
    shader.fallback_color = shader.color


def control_row(title, description, control):
    return st.Row(
        st.Column(st.Text(title, size=15, color=INK), caption(description, size=12),
                  width=460, expand=True, spacing=4, tight=True),
        control, height=62, spacing=14,
    )


def slider_row(title, slider, value_text):
    return st.Column(
        st.Row(st.Text(title, size=14, color=INK, expand=True), value_text,
               height=20, spacing=12),
        slider, spacing=0, tight=True,
    )


def renderer_note(page):
    return ("Software preview uses a flat fallback color. Choose OpenGL or Vulkan for live effects."
            if not getattr(page.renderer.context, "native_shader", False) else
            "Live previews share the application's window. Resize it to explore the layout.")


def run_example(builder, description, screens=("home",)):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--backend", choices=("opengl", "vulkan", "software"), default="opengl")
    parser.add_argument("--screen", choices=screens, default="home",
                        help="Open a specific demo screen at startup")
    args = parser.parse_args()

    def main(page):
        demo = builder(page)
        if args.screen != "home":
            demo["open_screen"](args.screen)

    st.run(main, backend=st.Renderer(args.backend))
