# Running in the Browser

Saturn's desktop runtime is started by saturn.run. The optional saturn.web, instead, runs a supported subset of controls using FastAPI,
WebSocket, and the browser Canvas. Web is a separate deployment path; it does not turn native window APIs into browser windows.

## Installing the optional dependencies

~~~powershell
uv add "saturn[web] @ git+https://github.com/the-OmegaLabs/Saturn.git"
~~~

If you are developing the Saturn repository examples:

~~~powershell
uv sync --extra web
uv run python examples/web_sessions.py
~~~

Open the local address printed by the terminal. The example supports standalone pages, shared sessions, synchronized text, named messages,
and scrolling lists.

## Creating a FastAPI application

~~~python
from saturn.web import create_app


def main(page):
    page.add(saturn.Text("Hello from a browser"))


app = create_app(main)
~~~

create_app returns a standard FastAPI app, which can mount routes like any other ASGI application. You can also use
saturn.web.run(main, host="127.0.0.1", port=8000) to start via Uvicorn.

If you mount into an existing FastAPI app, you need to hook the Saturn Web child
lifespan into the host lifespan. For details see [Web sessions](../web.md#fastapi-integration).

## Standalone views and shared sessions

By default, every browser connection gets its own Page. When you want two tabs to share the same control tree, pick the same session
before first modifying the Page:

~~~python
def main(page):
    page.web.session = "shared-counter"
    if not page.web.is_new_session:
        return
    page.add(saturn.Text("Shared page"))
~~~

Updates to shared controls are synchronized to the other views in the session. Viewport size, focus, cursor selection,
IME drafts, scroll positions, and animation playback progress remain the state of each individual browser view.

A custom session ID is only a state selector, not authentication. When deploying, use `authorize` to validate requests;
sensitive resources need their own authentication and authorization policies.

## Web's feature boundaries

The Web client uses Canvas 2D. Basic support includes text, buttons, input, layout, images,
ListView, AlertDialog, and SnackBar. Native file dialogs, subwindows, GPU shaders,
full TextField decorations, and all desktop events are not available.

Pages stay in the memory of the serving process; a service restart clears the sessions. The current registry is a single-process, in-memory
state; production deployments should use one worker, or provide their own consistent external session architecture.

## Key points of this chapter

saturn.web is another renderer and session layer on top of the shared control model. First read the
[Web sessions guide](../web.md) to understand event ordering, authorization, lifecycle, and coverage, then deploy
to real users.
