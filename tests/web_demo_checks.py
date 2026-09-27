"""Full demo behavior through the Web runtime, including native-call no-ops."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))

import saturn as st
from demo import Application
from saturn.web.app import WebRuntime
from saturn.web.context import current_view


async def check():
    runtime=WebRuntime(Application().create_window)
    async with runtime.lifespan():
        view=await runtime.connect(SimpleNamespace(query_params={}),dict(width=1280,height=900))
        origin=current_view.set(view)
        page=view.session.page
        assert page.window.width==1280 and page.window.height==900
        assert page.window.hwnd==page.window.native_handle==0
        page.window.width=12
        page.window.opacity=.1
        page.window.full_screen=True
        page.window.close();page.window.destroy()
        assert page.width==1280 and page.window.opacity==1
        assert not page.window.full_screen and not view.session.closed

        def node(kind,label=None):
            return next(n for n in view.scene['nodes'].values()
                        if n['kind']==kind and (label is None or n.get('text')==label))
        async def event(n,name,value=None):
            await runtime.receive(view,dict(type='event',id=str(len(view.seen_events)),
                control=n['id'],name=name,value=value))
            await asyncio.sleep(.025)
            assert not any(m['type']=='error' for m in list(view.outbox._queue))
        await event(node('button','Elevated'),'click')
        assert any(n.get('text')=='last event: click #1' for n in view.scene['nodes'].values())
        icon=next(n for n in view.scene['nodes'].values() if n.get('aria_label')=='Icon button')
        await event(icon,'click')
        assert any(n.get('text')=='last event: click #2' for n in view.scene['nodes'].values())
        slider=node('slider')
        await event(slider,'change',17)
        assert node('slider')['value']==20
        dropdown=node('select')
        await event(dropdown,'select','g')
        assert node('select')['value']=='g'
        assert any(n.get('text')=='select=g' for n in view.scene['nodes'].values())
        await event(node('button','Dialog'),'click')
        assert len(page.overlay)==1 and node('barrier')
        assert node('button','Elevated')['disabled']
        try:
            await runtime.receive(view,dict(type='scroll',control=node('scroll')['id'],offset=100))
        except ValueError:
            pass
        else:
            raise AssertionError('List behind dialog accepted scrolling')
        await event(node('button','Cancel'),'click')
        assert not page.overlay
        await event(node('button','SnackBar'),'click')
        assert len(page.overlay)==1 and any(n.get('text')=='Saved!' for n in view.scene['nodes'].values())
        await event(node('button','Undo'),'click')
        assert not page.overlay
        dismissed=[]
        dialog=st.AlertDialog(title='Dismiss once',on_dismiss=lambda e: dismissed.append((e.name,e.page)))
        await runtime.execute(view,[lambda:page.show_dialog(dialog)],None)
        await asyncio.sleep(.025)
        await event(node('barrier'),'dismiss')
        assert dismissed==[('dismiss',page)]
        snack=st.SnackBar('Timed',duration=30,persist=False)
        await runtime.execute(view,[lambda:page.show_dialog(snack)],None)
        await asyncio.sleep(.08)
        assert not page.overlay and not view.session.dialog_timers
        assert {'SaturnIcons','SaturnDefault'}<=view.scene['fonts'].keys()
        current_view.reset(origin)
    print('Full Web demo: window no-ops, controls, dialogs and timers passed')


if __name__=='__main__':
    asyncio.run(check())
