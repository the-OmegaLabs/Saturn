"""Deterministic cold/warm transition benchmark, without display vsync."""
import cProfile
import pstats
import statistics
import sys
import time
from types import SimpleNamespace

import pygame
import saturn as ft
from saturn.painting import _shadow, _scaled_shadow
from saturn.renderer import create_renderer


def run(backend='software'):
    pygame.init()
    window = pygame.Window(size=(640,480),hidden=True,opengl=backend=='opengl')
    r = create_renderer(backend,window,logical_size=(640,480))
    app = SimpleNamespace(size=(640,480),renderer=r,mark_dirty=lambda:None,
                          post=lambda fn:None,call=lambda fn,*args:fn(*args))
    page = ft.Page(app)
    toolbar = ft.FloatingToolbar(*[ft.IconButton(ft.Icons.ADD) for _ in range(3)],
                                 leading=ft.IconButton(ft.Icons.HOME),
                                 trailing=ft.IconButton(ft.Icons.SETTINGS))
    menu = ft.FloatingActionButtonMenu([
        ft.FloatingActionButtonMenuItem('Action '+str(i),icon=ft.Icons.ADD)
        for i in range(4)],expanded=True)
    page.add(toolbar,menu)
    menu._place(540,400,56,56,r.scale)
    # Load text and icons before isolating transition rendering costs.
    menu._overlay._place(0,0,640,480,r.scale)
    menu._overlay._draw_all(r)
    profiler=cProfile.Profile()
    profiler.enable()
    for cycle in range(2):
        if cycle==0:
            _shadow.cache_clear()
            _scaled_shadow.cache_clear()
        elapsed=[]
        for i in range(60):
            p=(i if i<30 else 59-i)/29
            toolbar._reveal=p
            menu._animate_internal('_reveal',p,0)
            start=time.perf_counter()
            r.clear('#FEF7FF')
            w,h=toolbar._intrinsic(None,None,r.scale)
            toolbar._place(20,20,w,h,r.scale)
            toolbar._draw_all(r)
            menu._overlay._place(0,0,640,480,r.scale)
            menu._overlay._draw_all(r)
            if backend=='opengl':
                r.ctx.finish()
            elapsed.append((time.perf_counter()-start)*1000)
        print(backend, 'cold' if cycle==0 else 'warm',
              'median_ms',round(statistics.median(elapsed),2),
              'p95_ms',round(sorted(elapsed)[56],2),
              'max_ms',round(max(elapsed),2), 'shadow_cache',_shadow.cache_info())
    profiler.disable()
    pstats.Stats(profiler).sort_stats('cumtime').print_stats(12)
    r.close();window.destroy();pygame.quit()


if __name__=='__main__':
    run(sys.argv[1] if len(sys.argv)>1 else 'software')
