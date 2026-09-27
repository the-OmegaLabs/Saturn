# Saturn Web architecture

**Status: design proposal. The Web runtime and these APIs are not implemented yet.**

## Goal

Add an optional `saturn.web` package using FastAPI/WebSocket and a browser
Canvas renderer. Application logic and authoritative state stay in Python.
The browser handles rendering, visual animation and immediate feedback.
The server sends scene changes and resource references rather than whole-page
screenshots or animation frames.

Web-specific services belong to `page.web`. Desktop native-window operations
belong to `page.window`. Existing `saturn.run()` keeps its desktop behavior.

## Sessions and browser views

A logical session owns one Page, its control tree, callbacks, route, theme/font
configuration and application state. Several browser views can attach to it.
Each new view receives a distinct random UUID4 session ID by default.

Assigning the same ID explicitly joins the same logical Page:

```python
def main(page):
    page.web.session = "project:123"
```

IDs are strings scoped to a Web app instance. A custom ID selects shared state;
membership permissions are checked separately. Default IDs use UUID4 without
hashing user/device information. MD5/SHA256 are unnecessary for this identity;
content hashes remain useful for immutable asset caches.

| Shared within a session | Local to each browser view |
| --- | --- |
| Control tree and persistent control properties | Viewport, display density and computed layout geometry |
| Text and accepted field values; Checkbox/Dropdown selected values | Keyboard focus, caret and text selection range |
| Visibility, disabled state and application data | Hover, pressed feedback, pointer state and scroll offsets |
| Page route, theme and font aliases | IME composition and unconfirmed input drafts |
| Callback registrations and animation targets | Resource readiness, acknowledgements and animation playback |

A control event executes its Python callback once. The accepted state is then
synchronized to all attached views. Applying an incoming update does not
execute the callback again. Separate sessions cannot observe each other's
controls, routes, themes, font aliases or subscriptions.

### Selecting and initializing a session

`main(page)` runs for each new view so the application can choose its session.
Set `page.web.session` before adding controls, registering subscriptions or
committing the first update. The Page handle binds to the selected session.

`page.web.is_new_session` identifies the initializer. Existing-session joins
reuse the current Page; application code skips rebuilding it:

```python
import saturn
from saturn.web import run


def main(page):
    page.web.session = "counter-demo"
    if not page.web.is_new_session:
        return

    label = saturn.Text("0")

    def increment(e):
        label.value = str(int(label.value) + 1)
        page.update()

    page.add(label, saturn.Button("Increment", on_click=increment))


run(main, host="127.0.0.1", port=8000)
```

Without the assignment, each view initializes its own independent Page.
Its default UUID is available before `main` runs.

Session creation/initialization is coordinated atomically. Simultaneous joins
nominate one initializer; other views wait for it to finish before receiving
a snapshot. Initialization failure is reported to waiting views and releases
the incomplete session; a later join can retry.

The first version fixes membership after initialization. Changing the ID after
controls/subscriptions/updates have been committed raises a clear error. A
later runtime-switching API needs explicit transition semantics so changing
one client's membership cannot accidentally move all participants.

### Web context

| Proposed API | Meaning |
| --- | --- |
| `page.web.session` | Session ID, writable during initial selection |
| `page.web.is_new_session` | Whether this entry invocation owns initialization |
| `page.web.client_id` | Originating browser-view ID inside entry functions/events; `None` for server-originated jobs |
| `page.web.connection_count` | Number of attached views in this session |
| `page.web.events` | Named message subscriptions and sending |
| `page.web.on_connect` | A view has joined an initialized Page |
| `page.web.on_disconnect` | A view disconnected; includes remaining connection count |

Views have distinct identities even when session IDs match. Originating view
information travels with events and callback execution context; it cannot be
one mutable field on a shared Page. Use an event's `client_id` when scheduling
work that outlives that callback.

Desktop Web-specific operations report that a Web runtime is required. Web
native-window operations such as `window.hwnd`, native positioning and owned
native Subpages are unsupported. Shared Page/Control APIs keep their ordinary
meanings; backend-specific capabilities are documented explicitly.

## Named messages

Keep the requested interface:

```python
page.web.events.subscribe(sub_name, handler)
page.web.events.unsubscribe(sub_name)
page.web.events.send(sub_name, data)
```

The default topic scope is the current logical session. The same topic name in
another session has independent subscribers. A subscription belongs to the
logical Page; attaching another view does not duplicate it.

Register handlers during Page initialization:

```python
def show_notice(e):
    status.value = str(e.data)
    page.update()

page.web.events.subscribe("notice", show_notice)
page.web.events.send("notice", {"text": "Saved", "item_id": 12})
page.web.events.unsubscribe("notice")
```

Handlers follow ordinary Saturn conventions: sync/async, zero arguments or
one event. The proposed message event contains `name`, `data`, `page`,
`session`, `client_id`, `message_id` and `sequence`. Server-originated messages
use `client_id=None`.

### Delivery contract

- `subscribe(name, handler)` adds a handler. Registering the same callable again
  on the same Page/topic is idempotent.
- `unsubscribe(name)` removes that Page's topic handlers. Optional `handler=`
  removes one handler; repeated removal is harmless.
- `send(name, data)` enqueues a message and returns its ID. Handlers are not
  called recursively inside `send`.
- Topics are nonempty strings. Payloads are JSON-safe strings, integers, finite
  floats, booleans, `None`, lists and string-keyed dictionaries. Values are
  copied/serialized at send time; later caller mutations do not alter queued
  messages. Unsupported values fail clearly.
- A logical subscriber receives a message once in a live process; attaching
  more browsers does not multiply callback execution. Page changes produced
  by handlers synchronize to all views.
- Messages and state commits are ordered per session. Awaiting async handlers
  preserves their order. Handler failures are reported without preventing
  other handlers from receiving the message.
- Messages sent from a handler run after the current dispatch. Long-running
  work uses a separate background-work path and submits a later state commit.
- Messages are transient by default. Reconnect restores current UI state,
  without replaying old messages or promising durable delivery.

### Cross-session notifications

An explicit optional scope supports notifications between independent Pages:

```python
page.web.events.subscribe("announcement", show_notice, scope="app")
page.web.events.send("announcement", "Maintenance at 18:00", scope="app")
page.web.events.unsubscribe("announcement", scope="app")
```

`scope="app"` reaches subscribed logical Pages in the Web app instance, once
per subscriber, without merging their state. The default is `scope="session"`.
Cross-session publication is an explicit server-side application operation;
browser messages cannot grant themselves that scope.

Ordinary control changes synchronize through `page.update()`. Named messages
are available for notifications and explicit coordination; no manual message
is needed for every control property change.

## Ordering, lifecycle and reconnect

Each session owns a serialized mutation queue and an increasing state revision.
Control events identify their originating view, event ID and input version.
Duplicate transport submissions are rejected within a bounded acknowledgement
window. Callbacks cannot concurrently mutate the same shared control tree.

An async callback preserves event order while it is awaited. External work
that would block the session queue must use a background-work API, then submit
a result with its expected revision when conflict detection is needed. A
handler cannot wait for a message it just enqueued while holding that queue.

Accepted input values are shared; drafts and composition are local. Input
acknowledgements carry the local edit version and accepted server revision.
Conflicting edits are reported so stale acceptance cannot overwrite a newer
draft. Initially use explicit conflict/reload behavior; collaborative document
merging is outside the first version.

A session remains alive while a view is attached. After the last disconnect,
retention is configurable, for example `create_app(main, session_ttl=300)`.
An authorized resume token restores a retained session. Expiration disposes
controls, callbacks, subscriptions and per-view resources. Immutable asset
caches may remain. Fresh views still receive distinct default sessions.

The initial registry and event service operate in one process. Multiple ASGI
workers require shared ownership/routing and message transport. In-memory
sessions do not span workers or survive a server restart; this limit must be
explicit in the first release.

## Server and browser responsibilities

| Capability | Python server | Browser view |
| --- | --- | --- |
| Business logic | Callbacks, validation and services | Input/event transport |
| State | Authoritative session Page | Scene replica and local interaction state |
| Layout | Initially calculates geometry separately for each view | Reports viewport, density and font readiness |
| Drawing | Stable scene nodes and resources | Canvas drawing, clipping, transforms and resource caching |
| Animation | Targets, durations, curves and versions | Local requestAnimationFrame interpolation |
| Input feedback | Declares supported interactions/styles | Immediate press, hover, focus, scrolling and caret feedback |
| Text editing | Accepts values and checks edit versions | Native input bridge, selection, clipboard and IME |
| Navigation | Shared session route and Page content | Navigation and browser history updates |

Scene nodes include interaction descriptions as well as drawing operations.
Canvas content also needs a DOM accessibility/keyboard layer.

## Package and FastAPI entry points

```text
saturn/web/
    __init__.py       # run, create_app, mount_app
    app.py            # ASGI integration and callback runtime
    session.py        # registry, Page ownership and view lifecycle
    events.py         # scoped subscriptions and ordered messages
    protocol.py       # versions, scene transactions and semantic input
    scene.py          # stable scene nodes and differences
    view.py           # per-view layout and interaction state
    resources.py      # immutable fonts/images and cache references
    static/
        index.html
        client.js     # WebSocket, state synchronization, input and animation
        renderer.js   # Canvas drawing
```

FastAPI and the ASGI runner are optional dependencies. `saturn.__init__` does
not import the Web package. Current main imports load desktop modules; headless
deployment also needs platform imports extracted or deferred.

`create_app(main)` returns a real FastAPI instance with UI, resource and
WebSocket routes. Users can add ordinary APIs, routers, middleware and lifespan
logic without a Saturn API-route wrapper:

```python
from fastapi import APIRouter
from saturn.web import create_app
import uvicorn

app = create_app(main)

@app.get("/api/health")
async def health():
    return {"status": "ok"}

router = APIRouter(prefix="/api/items")

@router.get("/")
async def list_items():
    return {"items": []}

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

`run(main)` is a convenience runner. `mount_app(app, main, path="/ui")` mounts
the UI in a host app. The outer app owns lifespan; initialization and cleanup
of mounted UI resources must be connected explicitly. Resource/WebSocket URLs
honor the mount path. UI routing does not consume unrelated API paths; HTTP
exceptions, responses and OpenAPI retain standard FastAPI behavior.

APIs and UI callbacks can call the same business services. APIs access session
state through an explicit authorized interface; they do not automatically
select one browser's Page.

## Runtime reuse and isolation

Extract callback/lifecycle/update behavior from desktop window creation, SDL
input and presentation. Web startup does not initialize a fake native window.
Use a shared runtime boundary rather than inheriting desktop App wholesale.

Desktop currently switches global theme/font settings between windows. Web
requires explicit session render configuration. Font/image source caches can
be shared; measurement keys include actual font and measurement parameters.

Current controls contain layout/interaction fields such as `_rect`, focus
and scroll positions. Separate those from shared logical state. Each view has
its own geometry, hit regions, measurement inputs and culling state. Resizing
one browser cannot change another's layout. Broadcasting identical coordinates
to different viewports is insufficient.

## Retained scene and protocol

Logical controls have stable session-local IDs. Drawing nodes use stable
sub-identities rather than transient draw-call positions. One control can emit
several nodes; events target the owner control. Nodes contain parent/order,
drawing kind, geometry, style, clipping, transforms, interactions and resources.

Initial connection sends a full view snapshot. Later transactions use `create`,
`patch`, `remove`, `reorder` and `animate`. Shared state revisions and view scene
revisions are distinct: a resize may change one scene without changing the Page.

```json
{
  "type": "patch",
  "state_revision": 7,
  "revision": 12,
  "base_revision": 11,
  "ops": [
    {"op": "patch", "id": "label-1", "props": {"text": "1"}},
    {"op": "animate", "id": "card-1", "property": "opacity",
     "to": 1, "duration_ms": 200, "curve": "ease_out", "version": 3}
  ]
}
```

Transactions apply atomically. Animation replacement is versioned and starts
from the displayed value. Initially receipt time is the playback origin;
nodes in one batch use the same origin. Playback remains view-local.

The protocol includes version negotiation, acknowledgements and resynchronizing
snapshots. Slow views have bounded pending data; coalesce unsent updates where
safe or replace them with a fresh snapshot. One slow view cannot block others
or accumulate unlimited stale updates. Idle state produces no scene messages.

## Input, scrolling and fonts

The browser hit-tests its displayed scene, including clipping/transforms.
The server validates membership, control ownership, allowed events and input
versions. Input identifies the displayed scene revision; the server cannot
hit-test against another view's geometry.

TextField text, selection, caret and IME use the same browser input element.
Accepted values synchronize; composition stays local. Server pygame measurement
and Surface text drawing need replacement interfaces for direct browser text.
Matching font files alone does not guarantee matching line breaks/baselines.

Scrolling is local. Views report visible ranges, and the server retains nearby
nodes with a preload margin. Desktop culling must not discard nodes needed
for smooth local scrolling. Long lists need range updates and valid height/
scroll geometry.

Images/fonts load through resource endpoints with stable IDs/content hashes.
Ordinary text and geometry remain scene operations rather than bitmaps.

## Canvas and effects

Start with Canvas 2D text, images, geometry, clipping and transforms. The
Renderer interface supplies useful primitives; existing Surface/text operations
need adaptation to stable scene nodes.

WebGL Shader support follows basic interaction. Send effect parameters/time
descriptions and execute visual computation in the browser. Desktop GLSL is
not assumed to run unchanged in WebGL. Capability limits and fallbacks are explicit.

## Implementation and acceptance

1. Define `page.web`, session selection/initialization ownership, UUID defaults,
   view identity and shared/local state boundaries.
2. Extract render configuration and view state from global/control fields.
   Implement one-process session ownership, callback ordering and scoped events.
3. Add optional FastAPI entry points and a basic Canvas scene protocol. Verify
   a counter, Chinese TextField and two independent views.
4. Verify shared-session views: one tree and callback execution, synchronized
   accepted state/route and independent focus/IME/layout/scroll.
5. Add local animation, visible ranges, backpressure, retained reconnect and
   explicit edit conflicts.
6. Extend controls/effects; then address multi-process ownership and transport.

Acceptance includes default isolation, simultaneous initial joins, rejected
late session reassignment, topic isolation, app-scope delivery, unsubscribe,
payload copying, callback failures, async order, disposal, node deletion and
reconnect/resynchronization under latency/jitter.

Animation does not require server frames; idle Pages send no redundant updates.
Chinese input remains continuous; stale acknowledgements do not replace newer
drafts. One view's resize/focus/scroll does not change another's. Custom APIs
and OpenAPI remain accessible; `/ui` generates correct resource/WebSocket URLs.
Desktop imports do not load Web dependencies.

## References

Flet informs server-driven UI, update protocols and event transport. Its Flutter
client renders controls; Saturn proposes its own retained Canvas scene and
initial server layout through a per-view context.

- [Flet client source](https://github.com/flet-dev/flet/blob/main/packages/flet/lib/src/flet_backend.dart)
- [Flet messaging protocol](https://github.com/flet-dev/flet/blob/main/sdk/python/packages/flet/src/flet/messaging/protocol.py)
- [Flet dynamic Web deployment](https://flet.dev/docs/publish/web/dynamic-website/)
- [FastAPI mounted applications](https://fastapi.tiangolo.com/advanced/sub-applications/)
- [Canvas usage and accessibility](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Basic_usage)
- [WebSocket API and backpressure](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
