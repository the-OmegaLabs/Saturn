"""Shared presentation settings for the Saturn demo gallery."""

from pathlib import Path

import saturn as ft


DEMO_WIDTH = 960
DEMO_HEIGHT = 800
LOGO = Path(__file__).resolve().parents[1] / "saturn-logo-transparent.png"


def brand_header(title: str, *, detail: str | None = None) -> ft.Row:
    controls = [
        ft.Image(str(LOGO), width=52, height=40,
                 fit=ft.BoxFit.CONTAIN, color=ft.Colors.PRIMARY),
        ft.Text(title, size=28, weight=ft.FontWeight.W_500,
                color=ft.Colors.ON_SURFACE),
    ]
    if detail:
        controls.append(ft.Text(detail, size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT))
    return ft.Row(controls, spacing=12,
                  vertical_alignment=ft.CrossAxisAlignment.CENTER)


def demo_panel(title: str, controls: list[ft.Control], *, width: int = 440) -> ft.Container:
    return ft.Container(
        ft.Column([
            ft.Text(title, size=18, weight=ft.FontWeight.W_500,
                    color=ft.Colors.ON_SURFACE),
            *controls,
        ], spacing=16, tight=True),
        width=width,
        padding=20,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border_radius=16,
    )
