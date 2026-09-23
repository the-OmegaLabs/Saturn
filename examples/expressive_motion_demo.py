"""Dark expressive motion gallery: --menu and --pressed snapshot states."""
import sys
import saturn
from demo_common import DEMO_HEIGHT, DEMO_WIDTH, brand_header


def main(page):
    page.title = 'Saturn · Expressive motion'
    page.theme = saturn.MaterialExpressiveTheme()
    page.theme_mode = saturn.ThemeMode.DARK
    page.padding, page.spacing = 24, 18
    status = saturn.Text('Morph · waves · floating actions', color=saturn.Colors.ON_SURFACE_VARIANT)
    def selected(e):
        status.value = f'Action: {e.control.content}'
        page.update()
    toolbar = saturn.FloatingToolbar(
        saturn.IconButton(saturn.Icons.EDIT, on_click=lambda e: toolbar.toggle()),
        saturn.IconButton(saturn.Icons.SHARE), saturn.IconButton(saturn.Icons.DELETE),
        leading=saturn.IconButton(saturn.Icons.HOME), trailing=saturn.IconButton(saturn.Icons.SETTINGS),
        vibrant=True)
    split = saturn.SplitButton('Split segment ripple', icon=saturn.Icons.PLAY_ARROW)
    if '--pressed' in sys.argv:
        segment = split.leading_button
        segment._state_press_alpha = .12
        segment._state_ripple_progress = 1
    menu = saturn.FloatingActionButtonMenu([
        saturn.FloatingActionButtonMenuItem(label,icon=icon,on_click=selected)
        for label,icon in [('New document',saturn.Icons.ADD), ('Upload',saturn.Icons.UPLOAD),
                           ('Share',saturn.Icons.SHARE), ('Archive',saturn.Icons.ARCHIVE)]
    ], expanded='--menu' in sys.argv)
    page.add(
        brand_header('Motion Demo'), status,
        saturn.Row([saturn.LoadingIndicator(width=64,height=64),
                saturn.LoadingIndicator(contained=True,width=64,height=64),
                *[saturn.LoadingIndicator(v,contained=True,width=48,height=48) for v in (0,.3,.7,1)]],
               spacing=24,vertical_alignment=saturn.CrossAxisAlignment.CENTER),
        saturn.Row([saturn.Column([saturn.WavyProgressIndicator(.6,width=320),
                           saturn.WavyProgressIndicator(width=320)],spacing=24,tight=True),
                saturn.CircularWavyProgressIndicator(.65),saturn.CircularWavyProgressIndicator()],
               spacing=32,vertical_alignment=saturn.CrossAxisAlignment.CENTER),
        saturn.Row([toolbar,saturn.TextButton('Collapse / expand',on_click=lambda e:toolbar.toggle())],
               spacing=24,vertical_alignment=saturn.CrossAxisAlignment.CENTER),
        saturn.Row([saturn.Button('A long label button with a soft shadow',width=420),split],spacing=20),
        saturn.ExtendedFloatingActionButton('Create a new document with a soft shadow',icon=saturn.Icons.ADD),
        saturn.TextField('Focus keeps the label gap open',label='Outlined input',width=500),
        saturn.Container(expand=True),
        saturn.Row([menu],alignment=saturn.MainAxisAlignment.END),
    )


if __name__ == '__main__':
    saturn.run(main,width=DEMO_WIDTH,height=DEMO_HEIGHT, backend=saturn.Renderer.VULKAN)
