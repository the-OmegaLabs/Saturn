# Saturn C++ (skeleton)

Agent-oriented C++ core. See [docs/AGENTS.md](docs/AGENTS.md) and [docs/DESIGN.md](docs/DESIGN.md).

## Build (Windows / MSVC + SDL3)

1. Install [SDL3 VC devel](https://github.com/libsdl-org/SDL/releases) (e.g. `SDL3-devel-*-VC.zip`).
2. From a VS x64 Developer Prompt:

```bat
cmake -S . -B build -DCMAKE_PREFIX_PATH=C:\path\to\SDL3-3.x.y
cmake --build build --config Release
copy C:\path\to\SDL3-3.x.y\lib\x64\SDL3.dll build\Release\
build\Release\saturn_hello.exe
```

Hello uses bundled `assets/Inter-Regular.ttf` (copied next to the exe on build).
Override with env `SATURN_FONT_PATH`. Missing font → `run()` throws (no silent bitmap fallback).
# C++ Usage

See [docs/CPP_GUIDE.md](docs/CPP_GUIDE.md) for the native rendering stack,
antialiasing, ownership conventions and typed API examples.
Build `saturn_counter` for a runnable usage example.
