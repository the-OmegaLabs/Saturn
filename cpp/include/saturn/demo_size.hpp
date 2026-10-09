#pragma once
namespace saturn {

// Demo size contract — see cpp/docs/DEMO.md.
//
// Three different things; do not collapse them under one "drawable" name:
//
// 1) Python OUTER intent (page.window.width/height / DEMO_WIDTH/HEIGHT).
// 2) LOGICAL CLIENT size passed to SDL_CreateWindow / SDL_GetWindowSize
//    (matches Windows true-GL golden client at 100% DPI).
// 3) PIXEL framebuffer (SDL_GetWindowSizeInPixels / GL viewport / SATURN_SHOT).
//    At 100% DPI, pixels == logical client. Under HiDPI, pixels = client * scale;
//    the shot contract below still expects 944x761 until scale is handled.

inline constexpr int kDemoOuterWidth = 960;   // Python outer intent
inline constexpr int kDemoOuterHeight = 800;

inline constexpr int kDemoClientWidth = 944;  // SDL logical client (CreateWindow)
inline constexpr int kDemoClientHeight = 761;

// Golden PNG pixel size at scale=1 (Windows true-GL). Equals kDemoClient* only
// when DPI scale is 1.0 — coincidence, not identity.
inline constexpr int kDemoGoldenPixelWidth = 944;
inline constexpr int kDemoGoldenPixelHeight = 761;

} // namespace saturn
