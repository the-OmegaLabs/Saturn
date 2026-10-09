#pragma once
// DEPRECATED for pixel parity: 5x7 bitmap cannot match Inter.
// Kept as emergency reference only. Text/FilledButton use saturn::Font (TTF).
// Define SATURN_USE_BITMAP_FONT only for experiments - not the demo path.
#include "saturn/limits.hpp"
#include "saturn/renderer.hpp"
#include "saturn/types.hpp"
#include <cstdint>
#include <stdexcept>
#include <string_view>
#include <vector>
namespace saturn {
namespace bitmap_font {
inline constexpr int kGlyphW = 5;
inline constexpr int kGlyphH = 7;
inline constexpr int kCellW = 6;
inline constexpr int kCellH = 8;
inline constexpr int kScale = 2;
inline constexpr int kAtlasCell = 8;   // 5x7 glyph + 1px pad
inline constexpr int kAtlasCols = 16;
inline constexpr int kAtlasRows = 8;   // ASCII 0..127

inline const std::uint8_t* glyph(char c) {
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

inline void build_atlas_rgba(std::vector<std::uint8_t>& rgba, int& tw, int& th) {
  tw = kAtlasCols * kAtlasCell;
  th = kAtlasRows * kAtlasCell;
  rgba.assign(std::size_t(tw * th * 4), 0);
  for (int ci = 0; ci < 128; ++ci) {
    const std::uint8_t* rows = glyph(static_cast<char>(ci));
    const int col0 = (ci % kAtlasCols) * kAtlasCell;
    const int row0 = (ci / kAtlasCols) * kAtlasCell;
    for (int row = 0; row < kGlyphH; ++row) {
      std::uint8_t bits = rows[row];
      for (int col = 0; col < kGlyphW; ++col) {
        if (bits & (1u << (kGlyphW - 1 - col))) {
          const int px = col0 + 1 + col;
          const int py = row0 + 1 + row;
          const std::size_t i = std::size_t(py * tw + px) * 4u;
          rgba[i] = 255;
          rgba[i + 1] = 255;
          rgba[i + 2] = 255;
          rgba[i + 3] = 255;
        }
      }
    }
  }
}

struct AtlasCache {
  void* tex = nullptr;
  Renderer* owner = nullptr;
};

inline AtlasCache& atlas_cache() {
  static AtlasCache c;
  return c;
}

inline void* ensure_atlas(Renderer& r) {
  AtlasCache& ac = atlas_cache();
  if (ac.tex && ac.owner == &r) return ac.tex;
  // Drop stale cache without destroy: owning OpenGLRenderer frees textures in dtor.
  ac.tex = nullptr;
  ac.owner = nullptr;
  static std::vector<std::uint8_t> pixels;
  static int tw = 0, th = 0;
  static bool built = false;
  if (!built) {
    build_atlas_rgba(pixels, tw, th);
    built = true;
  }
  void* tex = r.create_texture_rgba8(tw, th, pixels.data());
  if (!tex) throw std::runtime_error("bitmap_font atlas texture create failed");
  ac.tex = tex;
  ac.owner = &r;
  return tex;
}

inline void draw(Renderer& r, float x, float y, std::string_view text, Color color, float scale = float(kScale)) {
  if (text.size() > kMaxTextLen)
    throw std::invalid_argument("text exceeds kMaxTextLen");
  if (text.empty()) return;
  void* tex = ensure_atlas(r);
  std::vector<TexturedQuad> quads;
  quads.reserve(text.size());
  float cx = x;
  const float adv = float(kCellW) * scale;
  const float dw = float(kGlyphW) * scale;
  const float dh = float(kGlyphH) * scale;
  for (char raw : text) {
    const unsigned char ch = static_cast<unsigned char>(raw);
    if (ch != ' ') {
      const int ci = ch < 128 ? int(ch) : 0;
      const int col = ci % kAtlasCols;
      const int row = ci / kAtlasCols;
      TexturedQuad q;
      q.dst = Rect{cx, y, dw, dh};
      q.uv = Rect{
        float(col * kAtlasCell + 1),
        float(row * kAtlasCell + 1),
        float(kGlyphW),
        float(kGlyphH)};
      quads.push_back(q);
    }
    cx += adv;
  }
  if (!quads.empty())
    r.draw_textured_quads(tex, quads.data(), quads.size(), color);
}
}  // namespace bitmap_font
}  // namespace saturn
