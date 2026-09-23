# AndroidX Compose Material 3 源码参考

- 固定版本：`androidx.compose.material3:material3:1.5.0-alpha28`
- 下载日期：2026-09-23；通过 `http://127.0.0.1:7897` 代理下载。
- [Google Maven 官方源码包](https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3/1.5.0-alpha28/material3-1.5.0-alpha28-sources.jar)
- SHA-256：`df96abcc830f1cc28826da41a4dda2ac14d5a499b1ff67b0c97cd39b307e7aae`
- 许可证：Apache-2.0，原始许可证随源码保存在 `LICENSE.txt`。

`sources.jar` 是 ZIP 格式。实现位于
`commonMain/androidx/compose/material3/`，生成的设计参数位于其 `tokens/` 目录。
这是研究资料，不是 Saturn 的运行时依赖。

本机 Gradle 缓存另有 JetBrains `material3-desktop:1.9.0-alpha04` 源码；本次实现以此处固定的 AndroidX 版本为准。

## 生成形状资源

`saturn/_gen/loading_shapes.json` 的七个形状定义与此源码包中 `MaterialShapes.kt` 对应。
匹配曲线数据由本机缓存的 JetBrains `material3-desktop:1.9.0-alpha04` 与
AndroidX `graphics-shapes-desktop:1.0.1` 生成，使用 `RoundedPolygon` / `Morph` API。
这些库和派生几何数据适用 Apache-2.0；原始版权属于 Android Open Source Project。
`tools/ExportLoadingShapes.java` 可在配置这些 JAR 及 Kotlin/UI 支持库的 classpath 后再生成数据。
