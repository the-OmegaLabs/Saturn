"""Behavior checks for optional Web sessions; run directly with Python."""
import asyncio
import json
import time
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
from uuid import uuid4
import saturn as st
from saturn.web.app import WebRuntime
from saturn.web import create_app, mount_app


def request(room=None):
    return SimpleNamespace(query_params={"room": room} if room else {})


def drain(view):
    messages = []
    while not view.outbox.empty():
        messages.append(view.outbox.get_nowait())
    return messages


async def checks():
    builds, clicks, messages, changes = [], [], [], []
    async def main(page):
        if room := page.web.query.get("room"):
            page.web.session = room
        if not page.web.is_new_session:
            return
        await asyncio.sleep(.01)  # Exercise simultaneous first joins.
        builds.append(page.web.session)
        count = st.Text("0")
        def click(e):
            clicks.append(e.client_id)
            count.value = str(int(count.value)+1)
            page.update()
        field = st.TextField(width=240, on_change=lambda e: changes.append(e.data))
        listener = lambda e: messages.append((page.web.session, e.data, e.sequence))
        page.web.events.subscribe("hello", listener)
        page.web.events.subscribe("hello", listener)
        page.web.events.subscribe("broadcast", listener, scope="app")
        page.add(count, st.Button("Increment", on_click=click), field,
                 st.Checkbox("Shared"), st.ListView(controls=[st.Text(str(i), height=32)
                 for i in range(500)], height=128, item_extent=32, expand=True))

    runtime = WebRuntime(main, session_ttl=.05)
    hello = dict(type="hello", protocol=1, width=600, height=500)
    async with runtime.lifespan():
        a,b=await asyncio.gather(runtime.connect(request("shared"),hello),
                                 runtime.connect(request("shared"),dict(hello,width=350)))
        c,d=await asyncio.gather(runtime.connect(request(),hello),runtime.connect(request(),hello))
        assert a.session is b.session and c.session is not d.session
        assert builds.count("shared")==1 and len(runtime.sessions)==3
        assert a.client_id!=b.client_id
        assert a.scene['width']==600 and b.scene['width']==350
        assert a.scene['nodes'].keys()==b.scene['nodes'].keys()
        def node(view,kind):
            return next(n for n in view.scene['nodes'].values() if n['kind']==kind)
        button=node(a,'button')['id']; field=node(a,'input')['id']
        event=dict(type='event',id='click-1',control=button,name='click')
        await runtime.receive(a,event); await asyncio.sleep(.03)
        assert clicks==[a.client_id]
        assert node(a,'text')['text']==node(b,'text')['text']=='1'
        assert node(c,'text')['text']=='0'
        await runtime.receive(a,event); assert len(clicks)==1
        frozen=json.dumps(a.scene)
        await runtime.receive(b,dict(type='resize',width=280,height=450))
        assert json.dumps(a.scene)==frozen and b.scene['width']==280
        scroll=node(b,'scroll')['id']
        await runtime.receive(b,dict(type='scroll',control=scroll,offset=3000))
        assert a.scroll=={} and b.scroll[scroll]==3000
        assert len(b.scene['nodes'])<100
        assert any(n.get('text')=='93' for n in b.scene['nodes'].values())
        edit=dict(type='event',id='edit-1',control=field,name='change',value='中文 abc',version=1,input_revision=0)
        await runtime.receive(a,edit); await asyncio.sleep(.02)
        assert node(b,'input')['value']=='中文 abc' and changes==['中文 abc']
        await runtime.receive(a,edit); assert len(changes)==1
        await runtime.receive(b,dict(edit,id='conflict',value='lost',version=1))
        assert drain(b)[-1].get('conflict') and a.session.controls[field].value=='中文 abc'
        await runtime.receive(a,dict(edit,id='edit-2',value='fast',version=2))
        assert changes[-1]=='fast'
        payload={'items':[1]}
        a.session.page.web.events.send('hello',payload);payload['items'].append(2)
        await asyncio.sleep(.02)
        assert messages==[('shared',{'items':[1]},1)]
        a.session.page.web.events.unsubscribe('hello')
        a.session.page.web.events.send('hello','ignored');await asyncio.sleep(.02)
        assert len(messages)==1
        a.session.page.web.events.send('broadcast',{'all':True},scope='app');await asyncio.sleep(.03)
        assert {m[0] for m in messages[1:]}=={'shared',c.session.id,d.session.id}
        ordered=[]
        async def ordered_handler(e):
            await asyncio.sleep(.005)
            ordered.append(e.data)
        a.session.page.web.events.subscribe('ordered',ordered_handler)
        a.session.page.web.events.send('ordered',1)
        a.session.page.web.events.send('ordered',2)
        await asyncio.sleep(.03)
        assert ordered==[1,2]
        a.session.page.web.events.unsubscribe('ordered',handler=ordered_handler)
        for invalid in ({1:'bad'},float('nan'),object()):
            try:a.session.page.web.events.send('hello',invalid)
            except (TypeError,ValueError):pass
            else:raise AssertionError('invalid JSON accepted')
        try:a.session.page.web.session='other'
        except RuntimeError:pass
        else:raise AssertionError('late session switch accepted')
        a.session.controls[button].visible=False
        try:await runtime.receive(a,dict(event,id='hidden'))
        except ValueError:pass
        else:raise AssertionError('hidden control event accepted')
        removed=a.session.controls[button]
        a.session.page.remove(removed)
        await asyncio.sleep(.03)
        assert button not in a.scene['nodes'] and button not in a.session.controls
        drain(a);drain(b);await asyncio.sleep(.03)
        assert not drain(a) and not drain(b), 'Idle runtime produced frames'
        token=a.token;identifier=a.client_id
        await runtime.disconnect(a)
        resumed=await runtime.connect(request(),dict(hello,resume=token))
        assert resumed.session is b.session and resumed.client_id==identifier
        assert resumed.scroll=={} and not resumed.input_versions
        await runtime.disconnect(resumed);await runtime.disconnect(b)
        await asyncio.sleep(.08)
        assert 'shared' not in runtime.sessions and a.session.closed
        assert all(s is not a.session for s,_ in runtime.tokens.values())
    assert not runtime.sessions

    def limited_main(page):
        page.web.session='one'
        if page.web.is_new_session:page.add(st.Text('Only one logical session'))
    limited=WebRuntime(limited_main,max_sessions=1)
    async with limited.lifespan():
        view=await limited.connect(request(),hello)
        joined=await limited.connect(request(),hello)
        assert joined.session is view.session
        assert view.session.id=='one' and len(limited.sessions)==1

    denied=WebRuntime(main,authorize=lambda req,session:False)
    async with denied.lifespan():
        try:await denied.connect(request('secret'),hello)
        except PermissionError:pass
        else:raise AssertionError('authorization bypassed')

    from saturn import colors,text
    original=(colors.theme_dark,dict(text.registered_fonts),text.default_family)
    def font_main(page):
        dark=bool(page.web.query.get('room'))
        page.fonts={'Body':str(text.NOTO_REGULAR if dark else text.INTER)}
        page.theme=st.Theme(font_family='Body')
        page.theme_mode=st.ThemeMode.DARK if dark else st.ThemeMode.LIGHT
        page.add(st.Text('中文 font alias'))
    font_runtime=WebRuntime(font_main)
    async with font_runtime.lifespan():
        light=await font_runtime.connect(request(),hello)
        dark=await font_runtime.connect(request('dark'),hello)
        light_text=next(iter(light.scene['nodes'].values()))
        dark_text=next(iter(dark.scene['nodes'].values()))
        assert light_text['font']!=dark_text['font']
        assert light_text['color']!=dark_text['color']
        await font_runtime.refresh(light)
        assert next(iter(light.scene['nodes'].values()))==light_text
        assert original==(colors.theme_dark,dict(text.registered_fonts),text.default_family)


def protocol_checks():
    from starlette.testclient import TestClient
    with TestClient(create_app(lambda p:p.add(st.Text('hello')))) as client:
        assert client.get('/').status_code==200
        assert client.get('/static/client.js').status_code==200
        assert client.get('/resources/unknown').status_code==404
        with client.websocket_connect('/ws') as socket:
            socket.send_json(dict(type='hello',protocol=1,width=600,height=400))
            assert socket.receive_json()['type']=='welcome'
            scene=socket.receive_json()['scene']
            font=next(iter(scene['fonts'].values()))
            assert client.get('/resources/'+font).status_code==200
            socket.send_json(dict(type='event',id='bad',control='unknown',name='click'))
            assert socket.receive_json()['type']=='error'
            socket.send_json([])
            assert socket.receive_json()['type']=='error'
        try:
            with client.websocket_connect('/ws',headers={'origin':'https://other.example'}):pass
        except Exception:pass
        else:raise AssertionError('foreign Origin accepted')
    from fastapi import FastAPI
    host=FastAPI();child=mount_app(host,lambda p:p.add(st.Text('mounted')),path='/ui')
    with TestClient(host) as client:
        assert client.get('/ui/').status_code==200
        with client.websocket_connect('/ui/ws') as socket:
            socket.send_json(dict(type='hello',protocol=1))
            assert socket.receive_json()['type']=='welcome'
            assert socket.receive_json()['type']=='snapshot'
        client.portal.call(child.state.saturn.close)


async def stress():
    def main(page):
        page.add(st.Text('Ready'),st.ListView(controls=[st.Text(str(i),height=32)
                 for i in range(5000)],height=400,item_extent=32,expand=True))
    runtime=WebRuntime(main)
    async with runtime.lifespan():
        start=time.perf_counter()
        view=await runtime.connect(request(),dict(width=1200,height=800))
        first=(time.perf_counter()-start)*1000
        count=len(view.scene['nodes']);initial_size=len(json.dumps(view.scene))
        assert count<100
        timings=[]
        for width in range(600,1000,20):
            start=time.perf_counter()
            await runtime.receive(view,dict(type='resize',width=width,height=800))
            timings.append((time.perf_counter()-start)*1000)
        assert view.outbox.qsize()<=2, 'Unsent scenes were not coalesced'
        await runtime.receive(view,dict(type='scroll',control=next(n['id'] for n in
             view.scene['nodes'].values() if n['kind']=='scroll'),offset=150000))
        assert len(view.scene['nodes'])<100
        print(f'5,000 rows: first {first:.1f} ms; resize p95 {sorted(timings)[-2]:.1f} ms; '
              f'{count} scene nodes; {initial_size:,} snapshot bytes')


if __name__=='__main__':
    start=time.perf_counter()
    asyncio.run(checks());protocol_checks();asyncio.run(stress())
    print(f'Web session and protocol checks passed ({time.perf_counter()-start:.2f}s)')
