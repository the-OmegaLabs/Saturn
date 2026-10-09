# Saturn C++ (skeleton)

Agent-oriented C++ core for Saturn. See [docs/AGENTS.md](docs/AGENTS.md) and [docs/DESIGN.md](docs/DESIGN.md).

```bash
cmake -S . -B build -DCMAKE_PREFIX_PATH=/path/to/SDL3
cmake --build build
./build/saturn_hello
```

Phase ① stub: SDL3 window + clear/swap loop. OpenGL draw path fills in phase ②.
