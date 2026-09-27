# Web sessions

Saturn includes an optional FastAPI/WebSocket runtime and a Canvas 2D browser
client. Use `saturn.web` for browsers; `saturn.run()` starts native desktop apps.

## Install and run

```shell
uv sync --extra web
uv run --extra web python examples/web_sessions.py
```

Open `http://127.0.0.1:8000/` for an independent Page. Open
`http://127.0.0.1:8000/?room=demo` in two tabs to share a Page. The example
contains a shared counter, Chinese text input, checkbox, named messages,
routes, local opacity animation and a 500-row list with independent scrolling.

## Select shared state

```python
import saturn as st
from saturn.web import run

def main(page):
    page.web.session = "settings"
    if not page.web.is_new_session:
        return
    count = st.Text("0")
    def increment(e):
        count.value = str(int(count.value) + 1)
        page.update()
    page.add(count, st.Button("Increment", on_click=increment))

run(main)
```

Every new view receives a UUID4 session by default. `main` runs for each view so
it can select membership. Assign a custom ID **before** changing the Page,
adding controls, subscribing or updating. Guard shared initialization with
`page.web.is_new_session`. Simultaneous joins nominate one initializer and wait
for it to finish. Late session switches raise an error.

One session owns one tree and callback set. Accepted values, visibility, theme,
font aliases and route synchronize. Viewport, focus, caret, selection, IME
drafts, scroll and animation playback stay local. Call `page.update()` after
changing shared controls; ordinary state needs no manual notification.

| Web property | Meaning |
| --- | --- |
| `session` | Selected logical Page ID |
| `is_new_session` | This invocation owns initial construction |
| `client_id` | Originating view ID during entry/callback execution; otherwise `None` |
| `query` | Originating connection's URL query parameters |
| `connection_count` | Currently attached views |
| `on_connect`, `on_disconnect` | Sync/async callbacks with `e.client_id` and `e.connection_count` |
| `events` | Named, ordered server-side messages |

`page.width`, `page.height`, `page.media.device_pixel_ratio` and `page.focus()` use
the originating view. `page.on_resize` receives `e.width`, `e.height` and
`e.client_id`. `page.renderer.name` is `"canvas"`. Web `page.window` and native
Subpages are unavailable; desktop `page.web` reports the required runtime.

## Named messages

```python
def receive(e):
    label.value = str(e.data)
    page.update()

page.web.events.subscribe("notice", receive)
message_id = page.web.events.send("notice", {"saved": True, "items": [1, 2]})
page.web.events.unsubscribe("notice", handler=receive)  # Remove one handler.
page.web.events.unsubscribe("notice")                  # Remove all handlers.
```

The default scope is `"session"`; the same topic in another session is isolated.
Repeated subscription of the same callable is idempotent. Pass `scope="app"`
to subscription and sending to reach independent Pages once per subscriber,
including the sender, without merging state.

Payloads support strings, integers, finite floats, booleans, `None`, lists and
string-keyed dictionaries. Serialization copies payloads at send time; app
recipients get separate copies. Events expose `name`, `data`, `page`, `session`,
`client_id`, `message_id` and per-session `sequence`. Sending returns a UUID and
queues delivery. Sync/async handlers run in order; messages sent inside a
handler run later. Do not await a message queued behind the current handler.

## FastAPI integration

```python
from saturn.web import create_app
app = create_app(main, session_ttl=300)

@app.get("/health")
def health():
    return {"status": "ok"}
```

`create_app` returns an ordinary FastAPI app. `run(main, host="127.0.0.1",
port=8000, **options)` uses Uvicorn. Use one worker: the registry is in-memory
and scoped to this app instance.

To mount in an existing app, connect its lifespan explicitly. FastAPI does not
run mounted children's lifespans automatically:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from saturn.web import mount_app

@asynccontextmanager
async def lifespan(app):
    async with ui.state.saturn.lifespan():
        yield

app = FastAPI(lifespan=lifespan)
ui = mount_app(app, main, path="/ui")
```

Resources/WebSocket URLs honor `/ui/`; API routes and OpenAPI stay available.
Own long-running background work in the host lifespan. Page background tasks
and native services have no Web adapter yet.

| Runtime option | Default | Behavior |
| --- | --- | --- |
| `session_ttl` | `300` | Seconds to retain empty sessions and disconnected view tokens |
| `authorize` | `None` | Synchronous `(request, session_id) -> bool` check, including resume |
| `max_sessions` | `1024` | Logical session registry limit |
| `max_pending_events` | `256` | Callback queue limit per session |
| `max_message_bytes` | `65536` | Inbound message and named payload limit |
| `allowed_origins` | `None` | Same-origin browser connections; provide a list to allow other origins |

A shared ID selects state; it is not authentication. Use the authenticated
WebSocket request in `authorize`. Registered fonts/images are public cacheable
application assets; private documents need an authenticated resource adapter.

A memory-only resume token restores a retained Page and view identity. The
browser keeps it during temporary disconnection; reload creates a fresh view.
Reconnect sends current state and resets local interactions without replaying
messages. Server restart loses sessions and tokens.

## Rendering and current coverage

Basic controls: Text, Button and filled/tonal/outlined/text/elevated variants,
TextField, Checkbox, Switch, Container, Row, Column, Stack, Divider, local Image
and ListView. Switch currently uses a checkbox presentation. Button icons,
shadows, transforms, advanced field decoration, dialogs and WebGL effects are
not implemented. Shader draws its fallback color. Unsupported control types
fail explicitly; this is not a complete desktop-control port.
Control `on_size_change` is explicitly unsupported; use `page.on_resize`.

Fonts/images load by resource ID. Font aliases accept local browser-readable
files such as TTF, OTF and WOFF2. Remote fonts and TTC need adapters. Server
layout uses pygame font measurement; full-page bitmaps are never rendered or
transmitted. Browser shaping can differ from server wrapping. Theme defaults
to light; set `page.theme_mode` explicitly. Mixing live desktop and Web
renderers in one process is unsupported while font measurement uses scoped
global caches.

Scenes use stable IDs, snapshots and atomic patches; unsent frames coalesce
into a snapshot. Idle Pages send no render updates. Opacity animates with local
`requestAnimationFrame`; non-linear curves currently use smoothstep. Input
elements survive patches. Stale acknowledgements preserve newer drafts;
cross-view edits return explicit conflicts instead of overwriting accepted text.

Lists retain nearby rows with a 512-pixel preload margin. Wheel scrolling updates
locally before requesting a range. Use fixed row `height` or `item_extent`.
Fast jumps can briefly wait for new nodes. Layout is serialized and snapshots
are view-specific; private control `_rect` fields are temporary server scratch,
not a public per-view geometry API. Programmatic desktop scrolling and global
Page scrolling have no Web adapter yet.

## Verification

```shell
uv run --extra web --with httpx python tests/web_session_checks.py
```

Checks cover simultaneous joins, isolation, shared updates, edit conflicts,
duplicate events, async topic order, resize, scrolling, resume, expiration,
JSON validation, origin/membership rejection, mounts and a 5,000-row stress case.
On the development machine: 42 scene nodes / about 24 KB, initial layout about
98 ms, changing-width resize about 19–22 ms p95 after deduplicating font resource
lookups during layout. These are observations, not
performance guarantees.

See [Web architecture](./web-architecture.md) for future extensions.
