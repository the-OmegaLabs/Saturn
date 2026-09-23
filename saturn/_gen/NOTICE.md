# Expressive loading-shape geometry

`loading_shapes.json` contains generated, transformed geometry corresponding to AndroidX Compose Material 3 `1.5.0-alpha28` (`MaterialShapes.kt`). The matching cubic curves were generated using JetBrains Compose `material3-desktop:1.9.0-alpha04` and AndroidX `graphics-shapes-desktop:1.0.1`. This file is derived data, not a copy of the source archives.

`MaterialShapes.kt`: Copyright 2024 The Android Open Source Project. AndroidX Graphics Shapes source files include Copyright 2022 The Android Open Source Project. Licensed under the Apache License, Version 2.0. Saturn transformed the source geometry into matching Bézier control points for its own renderer.

- [AndroidX Compose Material 3 source archive](https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3-1.5.0-alpha28-sources.jar)
- SHA-256 of the pinned AndroidX source archive: `df96abcc830f1cc28826da41a4dda2ac14d5a499b1ff67b0c97cd39b307e7aae`
- [Apache License 2.0 text](./LICENSE-APACHE-2.0.txt)
- Generator: `tools/ExportLoadingShapes.java` in the repository root
