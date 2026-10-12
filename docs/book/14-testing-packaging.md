# Testing, Diagnostics, and Release

GUI applications can test business logic separately from view updates. Saturn pages depend on windows and renderers,
so simple unit tests should test state transitions first, and integration tests can then start a window to validate behavior and pixels.

## Testing business logic

If a click handler only modifies application state, you can test it directly:

~~~python
app = Application()
app.count = 0
app.increment(None)
assert app.count == 1
~~~

Larger applications can put state transitions into standalone functions and call those functions from control callbacks.
This way SDL doesn't need to be started in every business rule test.

## Running repository checks

The Saturn repository contains scripts for behavior, rendering, compatibility, and Web checks. Usually run from the repository root:

~~~powershell
uv run python tests/page_compatibility_checks.py
uv run python tests/flet_api_checks.py
uv run python tests/subpage_checks.py software
~~~

Checks related to the graphics card and desktop windows need a working graphics environment. Before committing, run only the tests relevant to the change
and supportable on the current machine, and record the GPU coverage that was not run.

## Diagnosing startup and GPU

Try the Software backend first:

~~~powershell
$env:SATURN_BACKEND = "software"
uv run python main.py
~~~

If the problem only appears with OpenGL or Vulkan, print page.renderer.name and
page.renderer.gpu_name, and register on_render_failed/on_render_ready.
They distinguish the "requested backend" from the "backend actually started".

## Checking where the package is imported from

~~~powershell
uv run python -c "import saturn; print(saturn.__file__)"
~~~

This same-named package is easily confused on PyPI, so the project currently recommends installing from the Saturn repository Git URL.
The project does not promise that wheels are available for all desktop platforms.

## Dependencies and assets

- Runtime library versions are locked through uv.lock;
- web, vulkan, cjk, and icons are optional extras;
- Images, fonts, and GLSL files should be distributed together as project resources;
- Use __file__-based paths to locate assets; do not depend on the working directory at startup;
- Font and image licenses must also be complied with and preserved with the application.

To build Saturn's own wheel, use the repository's tools/build-wheel.ps1. This script is for
contributors to the Saturn project; ordinary application developers should publish their own package with Saturn as a dependency.

## Compatibility checks before packaging

Check on the target machine:

1. Python version, SDL window, and GPU drivers;
2. Whether every control parameter used by the application is implemented;
3. Whether the UI remains interpretable under the Software fallback;
4. Whether fonts, images, GLSL, and data files are packaged;
5. The lifecycle when closing the main window, subwindows, and background tasks.

Saturn currently has no official cross-platform application packaging toolchain. Alpha releases require application
developers to choose and validate the packaging solution themselves.

## Key points of this chapter

Testing business state transitions is fast and stable; rendering, windows, and input need integration
checks in a graphics environment. Before release, pin dependencies, make asset paths explicit, and verify the feature boundaries your project actually uses.
