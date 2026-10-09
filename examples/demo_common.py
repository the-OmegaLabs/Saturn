"""Shared presentation settings for the Saturn demo gallery."""

from pathlib import Path

import saturn


# Outer window intent via page.window.width/height (see saturn.window._set_size).
# On Windows the drawable/client is smaller by the Win32 frame (~944x761);
# that client size is the C++ / SATURN_SHOT golden contract — do not treat
# these constants as framebuffer pixels.
DEMO_WIDTH = 960
DEMO_HEIGHT = 800
LOGO = Path(__file__).resolve().parents[1] / ".static" / "saturn-logo-transparent.png"


def brand_header(title: str, *, detail: str | None = None) -> saturn.Row:
    controls = [
        saturn.Image(str(LOGO), width=52, height=40,
                 fit=saturn.BoxFit.CONTAIN, color=saturn.Colors.PRIMARY),
        saturn.Text(title, size=28, weight=saturn.FontWeight.W_500,
                color=saturn.Colors.ON_SURFACE),
    ]
    if detail:
        controls.append(saturn.Text(detail, size=12,
                                color=saturn.Colors.ON_SURFACE_VARIANT))
    return saturn.Row(controls, spacing=12,
                  vertical_alignment=saturn.CrossAxisAlignment.CENTER)


def demo_panel(title: str, controls: list[saturn.Control], *, width: int = 440) -> saturn.Container:
    return saturn.Container(
        saturn.Column([
            saturn.Text(title, size=18, weight=saturn.FontWeight.W_500,
                    color=saturn.Colors.ON_SURFACE),
            *controls,
        ], spacing=16, tight=True),
        width=width,
        padding=20,
        bgcolor=saturn.Colors.SURFACE_CONTAINER_LOW,
        border_radius=16,
    )
