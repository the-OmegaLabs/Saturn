"""Expressive motion gallery: --dark, --menu and --pressed snapshot states."""
import sys
from pathlib import Path
import saturn as ft


def main(page):
    page.title = 'Saturn · Expressive motion'
    page.theme = ft.MaterialExpressiveTheme()
    page.theme_mode = ft.ThemeMode.DARK if '--dark' in sys.argv else ft.ThemeMode.LIGHT
    page.padding, page.spacing = 24, 18
    status = ft.Text('Morph · waves · floating actions', color=ft.Colors.ON_SURFACE_VARIANT)
    def selected(e):
        status.value = f'Action: {e.control.content}'
        page.update()
    toolbar = ft.FloatingToolbar(
        ft.IconButton(ft.Icons.EDIT, on_click=lambda e: toolbar.toggle()),
        ft.IconButton(ft.Icons.SHARE), ft.IconButton(ft.Icons.DELETE),
        leading=ft.IconButton(ft.Icons.HOME), trailing=ft.IconButton(ft.Icons.SETTINGS),
        vibrant=True)
    split = ft.SplitButton('Split segment ripple', icon=ft.Icons.PLAY_ARROW)
    if '--pressed' in sys.argv:
        segment = split.leading_button
        segment._state_press_alpha = .12
        segment._state_ripple_progress = 1
    menu = ft.FloatingActionButtonMenu([
        ft.FloatingActionButtonMenuItem(label,icon=icon,on_click=selected)
        for label,icon in [('New document',ft.Icons.ADD), ('Upload',ft.Icons.UPLOAD),
                           ('Share',ft.Icons.SHARE), ('Archive',ft.Icons.ARCHIVE)]
    ], expanded='--menu' in sys.argv)
    page.add(
        ft.Row([
            ft.Image(str(Path(__file__).resolve().parents[1] / 'saturn-logo-a2.svg'),
                     width=55, height=33, fit=ft.BoxFit.CONTAIN,
                     color=ft.Colors.PRIMARY),
            ft.Text('Expressive motion', size=28, weight=ft.FontWeight.W_500),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER), status,
        ft.Row([ft.LoadingIndicator(width=64,height=64),
                ft.LoadingIndicator(contained=True,width=64,height=64),
                *[ft.LoadingIndicator(v,contained=True,width=48,height=48) for v in (0,.3,.7,1)]],
               spacing=24,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([ft.Column([ft.WavyProgressIndicator(.6,width=320),
                           ft.WavyProgressIndicator(width=320)],spacing=24,tight=True),
                ft.CircularWavyProgressIndicator(.65),ft.CircularWavyProgressIndicator()],
               spacing=32,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([toolbar,ft.TextButton('Collapse / expand',on_click=lambda e:toolbar.toggle())],
               spacing=24,vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([ft.Button('A long label button with a soft shadow',width=420),split],spacing=20),
        ft.ExtendedFloatingActionButton('Create a new document with a soft shadow',icon=ft.Icons.ADD),
        ft.TextField('Focus keeps the label gap open',label='Outlined input',width=500),
        ft.Container(expand=True),
        ft.Row([menu],alignment=ft.MainAxisAlignment.END),
    )


if __name__ == '__main__':
    ft.run(main,width=920,height=800)
