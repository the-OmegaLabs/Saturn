# AndroidX Compose Material 3 source reference

- Pinned version: `androidx.compose.material3:material3:1.5.0-alpha28`
- Downloaded: 2026-09-23 through the `http://127.0.0.1:7897` proxy.
- [Official Google Maven source archive](https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3-1.5.0-alpha28-sources.jar)
- SHA-256: `df96abcc830f1cc28826da41a4dda2ac14d5a499b1ff67b0c97cd39b307e7aae`
- License: Apache-2.0. The original license is preserved in `LICENSE.txt`.

`sources.jar` is a ZIP archive. The implementation is in
`commonMain/androidx/compose/material3/`, and generated design parameters are in its `tokens/` directory.
This is research material, not a Saturn runtime dependency.

The local Gradle cache also contains the JetBrains `material3-desktop:1.9.0-alpha04` sources. This implementation uses the pinned AndroidX version above as its reference.

## Generating shape assets

The seven shapes in `saturn/_gen/loading_shapes.json` correspond to definitions in `MaterialShapes.kt` from this source archive.
Matching curve data was generated from locally cached JetBrains `material3-desktop:1.9.0-alpha04` and AndroidX `graphics-shapes-desktop:1.0.1` with the `RoundedPolygon` / `Morph` APIs.
Those libraries and the derived geometry data are covered by Apache-2.0; original copyright belongs to the Android Open Source Project.
`tools/ExportLoadingShapes.java` can regenerate the data after these JARs and Kotlin/UI support libraries are added to the classpath.
