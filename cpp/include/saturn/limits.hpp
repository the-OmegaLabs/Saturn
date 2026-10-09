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
} // namespace saturn
