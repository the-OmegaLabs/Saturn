# Installation and Running

## System requirements

- Python 3.10 or later;
- A desktop environment capable of running SDL;
- Working OpenGL drivers when using OpenGL;
- Vulkan drivers, the optional `vulkan` Python package, and the corresponding toolchain when using Vulkan.

Saturn is currently developed and validated mainly on Windows. Code paths for other platforms are under construction;
even if they start, you should first verify window, input, and font behavior.

## Running Saturn from source

This is how contributors and people who want to run the repository examples do it:

~~~powershell
git clone https://github.com/the-OmegaLabs/Saturn.git
cd Saturn
uv sync
uv run python examples/hello.py
~~~

You can also install an editable version into an already activated virtual environment:

~~~powershell
python -m pip install -e .
~~~

`uv sync` installs the default example groups from pyproject.toml. The browser examples require the `web` optional dependency:

~~~powershell
uv sync --extra web
~~~

Vulkan and the extra font and icon packages are separate optional extras:

~~~powershell
uv sync --extra vulkan
uv sync --extra cjk --extra icons
~~~

## Using Saturn in a new project

The Saturn repository lives at
[https://github.com/the-OmegaLabs/Saturn](https://github.com/the-OmegaLabs/Saturn). When installing, prefer using the Git URL explicitly:

~~~powershell
uv init hello-saturn
cd hello-saturn
uv add "saturn @ git+https://github.com/the-OmegaLabs/Saturn.git"
~~~

There is another Saturn date/time library with the same name on PyPI. Running `uv add saturn` or
`pip install saturn` directly may install the wrong package; if `Page`, `Text`, or `run` cannot be found after importing, check the install source first.

## Verifying the import

~~~powershell
uv run python -c "import saturn; print(saturn.__file__)"
~~~

The output should point to `saturn/__init__.py` in the current virtual environment or repository. Then run
`uv run python examples/hello.py`; if a window appears, the base installation is complete.

## Choosing the render backend

The default entry point selects OpenGL:

~~~python
saturn.run(main)
~~~

For diagnostics or when no GPU is available, you can choose the software backend:

~~~python
saturn.run(main, backend=saturn.Renderer.SOFTWARE)
~~~

The experimental Vulkan backend:

~~~python
saturn.run(main, backend=saturn.Renderer.VULKAN)
~~~

When `backend` is omitted, you can choose via an environment variable:

~~~powershell
$env:SATURN_BACKEND = "software"
uv run python main.py
~~~

If GPU initialization fails, OpenGL and Vulkan print a fallback notice and try software rendering.
The application can record this recovery through `page.on_render_failed` and `page.on_render_ready`.

## Next steps

Once installation is complete, follow the [project scaffold](../getting-started.md) to write your `main.py`. You don't need to learn every control; a rough understanding of this guide is enough, and you can consult the control APIs as needed.
