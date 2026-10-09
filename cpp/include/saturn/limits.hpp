#pragma once
#include <cstddef>
namespace saturn {
inline constexpr std::size_t kMaxTextBytes = 1u << 20;
inline constexpr std::size_t kMaxTextLen = 4096;       // chars per text draw
inline constexpr std::size_t kMaxFillRects = 16384;    // rects / textured quads per batch
inline constexpr std::size_t kMaxEventQueue = 4096;
inline constexpr std::size_t kMaxLayoutDim = 1u << 15;
inline constexpr std::size_t kMaxChildren = 1u << 14;
inline constexpr std::size_t kMaxPathBytes = 4096;
inline constexpr std::size_t kMaxClipDepth = 64;
// Soft caps for SDF rounded fill / stroke (also clamped to half min(w,h)).
inline constexpr float kMaxCornerRadius = 4096.f;
inline constexpr float kMaxStrokeWidth = 4096.f;
// ListView / scroll back-buffer (future): never allocate unbounded tile caches.
inline constexpr std::size_t kMaxListItems = 4096;
inline constexpr std::size_t kMaxScrollBackBytes = 1u << 22; // 4 MiB
inline constexpr std::size_t kMaxScreenshotPixels = 1u << 24; // ~16M px compare cap
// Font / TTF
inline constexpr float kMinFontPx = 1.f;
inline constexpr float kMaxFontPx = 512.f;
inline constexpr std::size_t kMaxFontFileBytes = 32u << 20; // 32 MiB
inline constexpr int kFontAtlasDim = 1024; // square atlas edge (<= kMaxLayoutDim)
// Image decode (stb_image): path length uses kMaxPathBytes; file bytes capped
// separately. Per-axis decode dim is tighter than kMaxLayoutDim so a square RGBA
// buffer cannot exceed kMaxScreenshotPixels (wired to STBI_MAX_DIMENSIONS).
inline constexpr std::size_t kMaxImageFileBytes = 32u << 20; // 32 MiB
inline constexpr int kMaxImageDecodeDim = 4096;
// Slider tick count: paint loops `divisions-1` times; reject unbounded.
inline constexpr int kMaxSliderDivisions = 1024;
// Dropdown menu rows; paint/hit loop options — reject unbounded.
inline constexpr std::size_t kMaxDropdownOptions = 256;
// AlertDialog modal stack + action row; SnackBar duration / queue.
// Dialog (barrier) and SnackBar (non-barrier) budgets are separate so eight
// SnackBars cannot starve AlertDialogs (and vice versa).
inline constexpr std::size_t kMaxDialogDepth = 8;
inline constexpr std::size_t kMaxDialogActions = 8;
inline constexpr std::size_t kMaxSnackBarQueue = 8;
inline constexpr int kMaxSnackBarDurationMs = 60000; // 60s
static_assert(kMaxImageDecodeDim > 0);
static_assert(static_cast<std::size_t>(kMaxImageDecodeDim) <= kMaxLayoutDim);
static_assert(static_cast<std::size_t>(kMaxImageDecodeDim) *
                  static_cast<std::size_t>(kMaxImageDecodeDim) <=
              kMaxScreenshotPixels);
} // namespace saturn
