"""Dark expressive gallery. Run with --check for layout checks."""
import sys

import saturn
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header


def check():
    for size, height in zip(("xsmall", "small", "medium", "large", "xlarge"),
                            (32, 40, 56, 96, 136)):
        assert saturn.ExpressiveButton("A", size=size)._intrinsic(None, None, 1)[1] == height
    toggle = saturn.ToggleButton("A")
    toggle._toggle()
    assert toggle.checked
    toggle.disabled = True
    toggle._toggle()
    assert toggle.checked
    split = saturn.SplitButton("Run")
    w, h = split._intrinsic(None, None, 1)
    split._place(0, 0, w, h, 1)
    boundary = split.leading_button._rect[2]
    assert split._hit_test(1, 20) is split.leading_button
    assert split._hit_test(boundary + 1, 20) is None
    assert split._hit_test(boundary + 3, 20) is split.trailing_button
    children = [saturn.ExpressiveButton("A", width=100) for _ in range(3)]
    group = saturn.ButtonGroup(children)
    group._active_child = children[1]
    group._press_progress = 1
    group._place(0, 0, 324, 40, 1)
    assert [c._rect[2] for c in children] == [92.5, 115, 92.5]
    assert group._hit_test(100, 20) is None  # space after the compressed first item
    for item, height in ((saturn.ListItem("A"), 56),
                         (saturn.ListItem("A", supporting="B"), 72),
                         (saturn.ListItem("A", overline="C", supporting="B"), 88)):
        assert item._intrinsic(300, None, 1)[1] == height
    print("EXPRESSIVE LAYOUT AND INTERACTION CHECKS PASS")


def main(page):
    page.title = "Saturn · Expressive"
    page.theme = saturn.MaterialExpressiveTheme()
    page.theme_mode = saturn.ThemeMode.DARK
    page.padding = 24
    page.spacing = 16
    status = saturn.Text("Expressive components", size=14,
                     color=saturn.Colors.ON_SURFACE_VARIANT)

    def clicked(event):
        status.value = f"Action: {type(event.control).__name__}"
        page.update()

    def selected(event):
        status.value = f"Toggle checked: {event.data}"
        page.update()

    page.add(
        brand_header("Expressive Demo"),
        status,
        saturn.Row([
            saturn.ExpressiveButton(label, icon=saturn.Icons.ADD, size=size, on_click=clicked)
            for label, size in (("XS", "xsmall"), ("Small", "small"),
                                ("Medium", "medium"), ("Large", "large"),
                                ("XL", "xlarge"))
        ], spacing=12, vertical_alignment=saturn.CrossAxisAlignment.CENTER),
        saturn.Row([
            saturn.ToggleButton("Toggle", icon=saturn.Icons.FAVORITE, on_change=selected),
            saturn.FilledTonalToggleButton("Selected", checked=True, on_change=selected),
            saturn.OutlinedToggleButton("Outline", on_change=selected),
            saturn.ExpressiveButton("Disabled", disabled=True),
            saturn.SplitButton("Run", icon=saturn.Icons.PLAY_ARROW,
                           on_click=clicked, on_trailing_click=clicked),
        ], spacing=12, vertical_alignment=saturn.CrossAxisAlignment.CENTER),
        saturn.ButtonGroup([
            saturn.ExpressiveButton(label, icon=icon, on_click=clicked)
            for label, icon in (("Edit", saturn.Icons.EDIT), ("Share", saturn.Icons.SHARE),
                                ("Save", saturn.Icons.SAVE))
        ]),
        saturn.Row([
            saturn.SmallFloatingActionButton(saturn.Icons.ADD, on_click=clicked),
            saturn.FloatingActionButton(saturn.Icons.EDIT, on_click=clicked),
            saturn.MediumFloatingActionButton(saturn.Icons.ADD, on_click=clicked),
            saturn.LargeFloatingActionButton(saturn.Icons.ADD, on_click=clicked),
            saturn.ExtendedFloatingActionButton("Create", icon=saturn.Icons.ADD,
                                           size="medium", on_click=clicked),
            saturn.ExpressiveIconButton(saturn.Icons.FAVORITE, size="medium",
                                    selected=True, bgcolor=saturn.Colors.SECONDARY_CONTAINER,
                                    on_click=clicked),
        ], spacing=20, vertical_alignment=saturn.CrossAxisAlignment.CENTER),
        saturn.Row([
            saturn.Column([
                saturn.ListItem("Your library", leading=saturn.Icon(saturn.Icons.FOLDER),
                            trailing="24", on_click=clicked, width=430),
                saturn.ListItem("Selected item", supporting="Expressive state and shape",
                            leading=saturn.Icon(saturn.Icons.FAVORITE), selected=True,
                            on_click=clicked, width=430),
                saturn.ListItem("Disabled item", supporting="Unavailable action",
                            leading=saturn.Icon(saturn.Icons.LOCK), disabled=True, width=430),
            ], spacing=4, tight=True),
            saturn.Column([
                saturn.TextField("Expressive", label="Outlined", width=430),
                saturn.TextField("Material 3", label="Filled", filled=True, width=430),
                saturn.Slider(value=.55, width=430, divisions=10),
                saturn.Row([saturn.ProgressRing(.65), saturn.ProgressBar(.6, width=360)],
                       vertical_alignment=saturn.CrossAxisAlignment.CENTER, spacing=16),
            ], spacing=16, tight=True),
        ], spacing=24),
    )


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        saturn.run(main, width=DEMO_WIDTH, height=DEMO_HEIGHT)
