#pragma once
#include "saturn/renderer.hpp"
#include "saturn/types.hpp"
#include <string_view>
#include <cstdint>
namespace saturn {
namespace bitmap_font {
inline constexpr int kGlyphW = 5;
inline constexpr int kGlyphH = 7;
inline constexpr int kCellW = 6; // +1 gap
inline constexpr int kCellH = 8;
inline constexpr int kScale = 2;

inline const std::uint8_t* glyph(char c) {
  // 7 rows, low 5 bits used
  static const std::uint8_t blank[7] = {0,0,0,0,0,0,0};
  static const std::uint8_t box[7] = {0x1f,0x11,0x11,0x11,0x11,0x1f,0};
  switch (c) {
    case ' ': { static const std::uint8_t g[7]={0,0,0,0,0,0,0}; return g; }
    case '!': { static const std::uint8_t g[7]={0x4,0x4,0x4,0x4,0,0x4,0}; return g; }
    case '.': { static const std::uint8_t g[7]={0,0,0,0,0,0x4,0}; return g; }
    case 'C': { static const std::uint8_t g[7]={0xe,0x11,0x10,0x10,0x11,0xe,0}; return g; }
    case 'H': { static const std::uint8_t g[7]={0x11,0x11,0x1f,0x11,0x11,0x11,0}; return g; }
    case 'I': { static const std::uint8_t g[7]={0xe,0x4,0x4,0x4,0x4,0xe,0}; return g; }
    case 'S': { static const std::uint8_t g[7]={0xe,0x11,0x10,0xe,0x1,0x1e,0}; return g; }
    case 'a': { static const std::uint8_t g[7]={0,0xe,0x1,0xf,0x11,0xf,0}; return g; }
    case 'c': { static const std::uint8_t g[7]={0,0xe,0x10,0x10,0xe,0,0}; return g; }
    case 'e': { static const std::uint8_t g[7]={0,0xe,0x11,0x1f,0x10,0xe,0}; return g; }
    case 'f': { static const std::uint8_t g[7]={0x6,0x8,0x8,0x1c,0x8,0x8,0}; return g; }
    case 'i': { static const std::uint8_t g[7]={0x4,0,0x4,0x4,0x4,0x4,0}; return g; }
    case 'k': { static const std::uint8_t g[7]={0x10,0x10,0x12,0x1c,0x12,0x11,0}; return g; }
    case 'l': { static const std::uint8_t g[7]={0x8,0x8,0x8,0x8,0x8,0x8,0}; return g; }
    case 'm': { static const std::uint8_t g[7]={0,0x1b,0x15,0x15,0x15,0x15,0}; return g; }
    case 'n': { static const std::uint8_t g[7]={0,0x16,0x19,0x11,0x11,0x11,0}; return g; }
    case 'o': { static const std::uint8_t g[7]={0,0xe,0x11,0x11,0x11,0xe,0}; return g; }
    case 'r': { static const std::uint8_t g[7]={0,0x16,0x18,0x10,0x10,0x10,0}; return g; }
    case 's': { static const std::uint8_t g[7]={0,0xe,0x10,0xe,0x1,0x1e,0}; return g; }
    case 't': { static const std::uint8_t g[7]={0x8,0x8,0x1c,0x8,0x8,0x8,0}; return g; }
    case 'u': { static const std::uint8_t g[7]={0,0x11,0x11,0x11,0x13,0xd,0}; return g; }
    case 'w': { static const std::uint8_t g[7]={0,0x11,0x11,0x15,0x15,0xa,0}; return g; }
    default: return box;
  }
}

inline Size measure(std::string_view text, float scale = float(kScale)) {
  return {float(text.size()) * kCellW * scale, kCellH * scale};
}

inline void draw(Renderer& r, float x, float y, std::string_view text, Color color, float scale = float(kScale)) {
  float cx = x;
  for (char ch : text) {
    const std::uint8_t* rows = glyph(ch);
    for (int row = 0; row < kGlyphH; ++row) {
      std::uint8_t bits = rows[row];
      for (int col = 0; col < kGlyphW; ++col) {
        if (bits & (1u << (kGlyphW - 1 - col))) {
          r.fill_rect(Rect{cx + col * scale, y + row * scale, scale, scale}, color, 0);
        }
      }
    }
    cx += kCellW * scale;
  }
}
}  // namespace bitmap_font
}  // namespace saturn
