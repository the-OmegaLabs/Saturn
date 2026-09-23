"""Expressive gallery. Run with --dark or --check."""
import sys
from pathlib import Path

import saturn as ft


def check():
    for size, height in zip(("xsmall", "small", "medium", "large", "xlarge"),
                            (32, 40, 56, 96, 136)):
        assert ft.ExpressiveButton("A", size=size)._intrinsic(None, None, 1)[1] == height
    toggle = ft.ToggleButton("A")
    toggle._toggle()
    assert toggle.checked
    toggle.disabled = True
    toggle._toggle()
    assert toggle.checked
    split = ft.SplitButton("Run")
    w, h = split._intrinsic(None, None, 1)
    split._place(0, 0, w, h, 1)
    boundary = split.leading_button._rect[2]
    assert split._hit_test(1, 20) is split.leading_button
    assert split._hit_test(boundary + 1, 20) is None
    assert split._hit_test(boundary + 3, 20) is split.trailing_button
    children = [ft.ExpressiveButton("A", width=100) for _ in range(3)]
    group = ft.ButtonGroup(children)
    group._active_child = children[1]
    group._press_progress = 1
    group._place(0, 0, 324, 40, 1)
    assert [c._rect[2] for c in children] == [92.5, 115, 92.5]
    assert group._hit_test(100, 20) is None  # space after the compressed first item
    for item, height in ((ft.ListItem("A"), 56),
                         (ft.ListItem("A", supporting="B"), 72),
                         (ft.ListItem("A", overline="C", supporting="B"), 88)):
        assert item._intrinsic(300, None, 1)[1] == height
    print("EXPRESSIVE LAYOUT AND INTERACTION CHECKS PASS")


def main(page):
    page.title = "Saturn · Expressive"
    page.theme = ft.MaterialExpressiveTheme()
    page.theme_mode = ft.ThemeMode.DARK if "--dark" in sys.argv else ft.ThemeMode.LIGHT
    page.padding = 24
    page.spacing = 16
    status = ft.Text("Expressive components", size=14,
                     color=ft.Colors.ON_SURFACE_VARIANT)

    def clicked(event):
        status.value = f"Action: {type(event.control).__name__}"
        page.update()

    def selected(event):
        status.value = f"Toggle checked: {event.data}"
        page.update()

    page.add(
        ft.Row([
            ft.Image(str(Path(__file__).resolve().parents[1] / 'saturn-logo.svg'),
                     width=36, height=36, fit=ft.BoxFit.CONTAIN),
            ft.Text("Material 3 Expressive", size=28, weight=ft.FontWeight.W_500),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        status,
        ft.Row([
            ft.ExpressiveButton(label, icon=ft.Icons.ADD, size=size, on_click=clicked)
            for label, size in (("XS", "xsmall"), ("Small", "small"),
                                ("Medium", "medium"), ("Large", "large"),
                                ("XL", "xlarge"))
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([
            ft.ToggleButton("Toggle", icon=ft.Icons.FAVORITE, on_change=selected),
            ft.FilledTonalToggleButton("Selected", checked=True, on_change=selected),
            ft.OutlinedToggleButton("Outline", on_change=selected),
            ft.ExpressiveButton("Disabled", disabled=True),
            ft.SplitButton("Run", icon=ft.Icons.PLAY_ARROW,
                           on_click=clicked, on_trailing_click=clicked),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.ButtonGroup([
            ft.ExpressiveButton(label, icon=icon, on_click=clicked)
            for label, icon in (("Edit", ft.Icons.EDIT), ("Share", ft.Icons.SHARE),
                                ("Save", ft.Icons.SAVE))
        ]),
        ft.Row([
            ft.SmallFloatingActionButton(ft.Icons.ADD, on_click=clicked),
            ft.FloatingActionButton(ft.Icons.EDIT, on_click=clicked),
            ft.MediumFloatingActionButton(ft.Icons.ADD, on_click=clicked),
            ft.LargeFloatingActionButton(ft.Icons.ADD, on_click=clicked),
            ft.ExtendedFloatingActionButton("Create", icon=ft.Icons.ADD,
                                           size="medium", on_click=clicked),
            ft.ExpressiveIconButton(ft.Icons.FAVORITE, size="medium",
                                    selected=True, bgcolor=ft.Colors.SECONDARY_CONTAINER,
                                    on_click=clicked),
        ], spacing=20, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([
            ft.Column([
                ft.ListItem("Your library", leading=ft.Icon(ft.Icons.FOLDER),
                            trailing="24", on_click=clicked, width=430),
                ft.ListItem("Selected item", supporting="Expressive state and shape",
                            leading=ft.Icon(ft.Icons.FAVORITE), selected=True,
                            on_click=clicked, width=430),
                ft.ListItem("Disabled item", supporting="Unavailable action",
                            leading=ft.Icon(ft.Icons.LOCK), disabled=True, width=430),
            ], spacing=4, tight=True),
            ft.Column([
                ft.TextField("Expressive", label="Outlined", width=430),
                ft.TextField("Material 3", label="Filled", filled=True, width=430),
                ft.Slider(value=.55, width=430, divisions=10),
                ft.Row([ft.ProgressRing(.65), ft.ProgressBar(.6, width=360)],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=16),
            ], spacing=16, tight=True),
        ], spacing=24),
    )


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        ft.run(main, width=960, height=800)
