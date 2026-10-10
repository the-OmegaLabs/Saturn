#include "saturn/font.hpp"
#include "saturn/limits.hpp"
#include "saturn/renderer.hpp"
#include <SDL3/SDL.h>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <unordered_map>
#include <vector>

#define STB_TRUETYPE_IMPLEMENTATION
#define STBTT_STATIC
#include "stb_truetype.h"

namespace saturn {
namespace {

void check_px(float px) {
  if (!std::isfinite(px)) throw std::invalid_argument("font px_size non-finite");
  if (px < kMinFontPx || px > kMaxFontPx)
    throw std::invalid_argument("font px_size out of range");
}

float clamp_px(float px) {
  check_px(px);
  return px;
}

// Decode one UTF-8 codepoint; returns U+FFFD on invalid; advances i.
std::uint32_t next_codepoint(std::string_view s, std::size_t& i) {
  if (i >= s.size()) return 0;
  const auto b0 = static_cast<unsigned char>(s[i++]);
  if (b0 < 0x80) return b0;
  if ((b0 & 0xE0) == 0xC0) {
    if (i >= s.size()) return 0xFFFD;
    const auto b1 = static_cast<unsigned char>(s[i++]);
    if ((b1 & 0xC0) != 0x80) return 0xFFFD;
    return (std::uint32_t(b0 & 0x1F) << 6) | (b1 & 0x3F);
  }
  if ((b0 & 0xF0) == 0xE0) {
    if (i + 1 >= s.size()) return 0xFFFD;
    const auto b1 = static_cast<unsigned char>(s[i++]);
    const auto b2 = static_cast<unsigned char>(s[i++]);
    if ((b1 & 0xC0) != 0x80 || (b2 & 0xC0) != 0x80) return 0xFFFD;
    return (std::uint32_t(b0 & 0x0F) << 12) | (std::uint32_t(b1 & 0x3F) << 6) | (b2 & 0x3F);
  }
  if ((b0 & 0xF8) == 0xF0) {
    if (i + 2 >= s.size()) return 0xFFFD;
    const auto b1 = static_cast<unsigned char>(s[i++]);
    const auto b2 = static_cast<unsigned char>(s[i++]);
    const auto b3 = static_cast<unsigned char>(s[i++]);
    if ((b1 & 0xC0) != 0x80 || (b2 & 0xC0) != 0x80 || (b3 & 0xC0) != 0x80) return 0xFFFD;
    return (std::uint32_t(b0 & 0x07) << 18) | (std::uint32_t(b1 & 0x3F) << 12) |
           (std::uint32_t(b2 & 0x3F) << 6) | (b3 & 0x3F);
  }
  return 0xFFFD;
}

std::vector<std::uint8_t> read_file_capped(const std::string& path) {
  if (path.size() > kMaxPathBytes) throw std::invalid_argument("font path exceeds kMaxPathBytes");
  std::ifstream in(path, std::ios::binary | std::ios::ate);
  if (!in) throw std::runtime_error("font file open failed: " + path);
  const auto end = in.tellg();
  if (end < 0) throw std::runtime_error("font file size failed: " + path);
  const auto sz = static_cast<std::uint64_t>(end);
  if (sz == 0 || sz > kMaxFontFileBytes)
    throw std::runtime_error("font file size rejected: " + path);
  in.seekg(0);
  std::vector<std::uint8_t> buf(static_cast<std::size_t>(sz));
  if (!in.read(reinterpret_cast<char*>(buf.data()), static_cast<std::streamsize>(buf.size())))
    throw std::runtime_error("font file read failed: " + path);
  return buf;
}

struct GlyphInfo {
  int x = 0, y = 0, w = 0, h = 0;
  float xoff = 0, yoff = 0, advance = 0;
};

struct Atlas {
  Renderer* owner = nullptr;
  void* tex = nullptr;
  int dim = 0;
  int pen_x = 1;
  int pen_y = 1;
  int row_h = 0;
  float bake_px = 0;
  std::vector<std::uint8_t> rgba;
  std::unordered_map<std::uint32_t, GlyphInfo> glyphs;

  void reset_cpu(int d) {
    dim = d;
    pen_x = 1;
    pen_y = 1;
    row_h = 0;
    glyphs.clear();
    rgba.assign(std::size_t(d) * std::size_t(d) * 4u, 0);
  }

  void drop_gpu() {
    // Owning OpenGLRenderer frees textures in dtor; do not destroy here across owners.
    tex = nullptr;
    owner = nullptr;
  }
};

} // namespace

struct Font::Impl {
  std::string path;
  std::vector<std::uint8_t> file;
  stbtt_fontinfo info{};
  // One atlas per integer px (rounded). Process-level; GPU tex invalidated when Renderer changes.
  mutable std::unordered_map<int, Atlas> atlases;

  float scale_for(float px) const {
    // pygame/SDL_ttf font size is em pixels, not ascent-minus-descent height.
    return stbtt_ScaleForMappingEmToPixels(&info, px);
  }

  void metrics(float px, float& asc, float& desc, float& gap) const {
    int a = 0, d = 0, g = 0;
    stbtt_GetFontVMetrics(&info, &a, &d, &g);
    const float s = scale_for(px);
    asc = float(a) * s;
    desc = float(-d) * s; // positive below baseline
    gap = float(g) * s;
  }

  GlyphInfo& ensure_glyph(Atlas& at, std::uint32_t cp) const {
    auto it = at.glyphs.find(cp);
    if (it != at.glyphs.end()) return it->second;

    const float s = scale_for(at.bake_px);
    int advance = 0, lsb = 0;
    stbtt_GetCodepointHMetrics(&info, int(cp), &advance, &lsb);
    int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
    stbtt_GetCodepointBitmapBox(&info, int(cp), s, s, &x0, &y0, &x1, &y1);
    const int gw = x1 - x0;
    const int gh = y1 - y0;

    GlyphInfo g;
    g.advance = float(advance) * s;
    g.xoff = float(x0);
    g.yoff = float(y0);
    g.w = gw;
    g.h = gh;

    if (gw > 0 && gh > 0) {
      if (gw > at.dim - 2 || gh > at.dim - 2)
        throw std::runtime_error("glyph exceeds font atlas");
      if (at.pen_x + gw + 1 >= at.dim) {
        at.pen_x = 1;
        at.pen_y += at.row_h + 1;
        at.row_h = 0;
      }
      if (at.pen_y + gh + 1 >= at.dim)
        throw std::runtime_error("font atlas full (kFontAtlasDim)");
      std::vector<std::uint8_t> alpha(std::size_t(gw * gh));
      stbtt_MakeCodepointBitmap(&info, alpha.data(), gw, gh, gw, s, s, int(cp));
      for (int row = 0; row < gh; ++row) {
        for (int col = 0; col < gw; ++col) {
          const std::uint8_t a = alpha[std::size_t(row * gw + col)];
          const int px = at.pen_x + col;
          const int py = at.pen_y + row;
          const std::size_t i = (std::size_t(py) * std::size_t(at.dim) + std::size_t(px)) * 4u;
          at.rgba[i] = 255;
          at.rgba[i + 1] = 255;
          at.rgba[i + 2] = 255;
          at.rgba[i + 3] = a;
        }
      }
      g.x = at.pen_x;
      g.y = at.pen_y;
      at.pen_x += gw + 1;
      if (gh > at.row_h) at.row_h = gh;
      // New pixels - force GPU reupload on next ensure_tex.
      if (at.tex) at.drop_gpu();
    }

    auto [ins, _] = at.glyphs.emplace(cp, g);
    return ins->second;
  }

  Atlas& atlas_for(float px) const {
    const int key = int(std::lround(px));
    Atlas& at = atlases[key];
    if (at.dim == 0) {
      static_assert(kFontAtlasDim <= int(kMaxLayoutDim), "atlas dim cap");
      at.reset_cpu(kFontAtlasDim);
      // Supersample cached glyphs only, not the framebuffer or every paint call.
      at.bake_px = std::min(float(key)*2.f,kMaxFontPx);
      // Preload printable ASCII so hello / buttons do not thrash uploads.
      for (std::uint32_t cp = 32; cp < 127; ++cp) ensure_glyph(at, cp);
    }
    return at;
  }

  void* ensure_tex(Renderer& r, Atlas& at) const {
    if (at.tex && at.owner == &r) return at.tex;
    at.drop_gpu();
    void* tex = r.create_texture_rgba8(at.dim, at.dim, at.rgba.data());
    if (!tex) throw std::runtime_error("font atlas texture create failed");
    at.tex = tex;
    at.owner = &r;
    return tex;
  }
};

Font::Font(std::unique_ptr<Impl> impl) : impl_(std::move(impl)) {}
Font::Font(Font&&) noexcept = default;
Font& Font::operator=(Font&&) noexcept = default;
Font::~Font() = default;

Font Font::load(std::string path) {
  auto impl = std::make_unique<Impl>();
  impl->path = std::move(path);
  impl->file = read_file_capped(impl->path);
  if (!stbtt_InitFont(&impl->info, impl->file.data(),
                      stbtt_GetFontOffsetForIndex(impl->file.data(), 0))) {
    throw std::runtime_error("stbtt_InitFont failed: " + impl->path);
  }
  return Font(std::move(impl));
}

Font Font::load_default() {
  if (const char* env = std::getenv("SATURN_FONT_PATH")) {
    if (env[0] != '\0') return load(std::string(env));
  }
  std::vector<std::string> candidates;
  if (const char* base = SDL_GetBasePath()) {
    candidates.push_back(std::string(base) + "assets/Inter-Regular.ttf");
    // SDL3 owns its cached base-path string.
  }
  candidates.push_back("assets/Inter-Regular.ttf");
  candidates.push_back("cpp/assets/Inter-Regular.ttf");
  std::string errors;
  for (const auto& p : candidates) {
    try {
      return load(p);
    } catch (const std::exception& e) {
      if (!errors.empty()) errors += "; ";
      errors += p + ": " + e.what();
    }
  }
  throw std::runtime_error(
      "default font not found (set SATURN_FONT_PATH or ship assets/Inter-Regular.ttf): " + errors);
}

const std::string& Font::path() const { return impl_->path; }

Size Font::measure(std::string_view text, float px_size) const {
  if (text.size() > kMaxTextLen) throw std::invalid_argument("text exceeds kMaxTextLen");
  px_size = clamp_px(px_size);
  float asc = 0, desc = 0, gap = 0;
  impl_->metrics(px_size, asc, desc, gap);
  float w = 0.f;
  std::size_t i = 0;
  while (i < text.size()) {
    const std::uint32_t cp = next_codepoint(text, i);
    if (cp == 0) break;
    int advance = 0, lsb = 0;
    stbtt_GetCodepointHMetrics(&impl_->info, int(cp), &advance, &lsb);
    w += float(advance) * impl_->scale_for(px_size);
  }
  return {w, asc + desc};
}

float Font::ascent(float px_size) const {
  px_size = clamp_px(px_size);
  float a, d, g;
  impl_->metrics(px_size, a, d, g);
  return a;
}

float Font::descent(float px_size) const {
  px_size = clamp_px(px_size);
  float a, d, g;
  impl_->metrics(px_size, a, d, g);
  return d;
}

float Font::line_height(float px_size) const {
  px_size = clamp_px(px_size);
  float a, d, g;
  impl_->metrics(px_size, a, d, g);
  return float(std::nearbyint(px_size*10.f/7.f));
}

void Font::draw(Renderer& r, float x, float y, std::string_view text, Color color, float px_size) const {
  if (text.size() > kMaxTextLen) throw std::invalid_argument("text exceeds kMaxTextLen");
  if (text.empty()) return;
  px_size = clamp_px(px_size);
  Atlas& at = impl_->atlas_for(px_size);
  // Ensure all glyphs packed before upload.
  {
    std::size_t i = 0;
    while (i < text.size()) {
      const std::uint32_t cp = next_codepoint(text, i);
      if (cp == 0) break;
      if (cp != ' ') impl_->ensure_glyph(at, cp);
      else impl_->ensure_glyph(at, cp); // space still needs advance in map
    }
  }
  void* tex = impl_->ensure_tex(r, at);
  float asc = 0, desc = 0, gap = 0;
  impl_->metrics(px_size, asc, desc, gap);
  const float baseline = y + asc;
  const float glyph_scale = px_size/at.bake_px;

  std::vector<TexturedQuad> quads;
  quads.reserve(std::min(text.size(), kMaxFillRects));
  float cx = x;
  std::size_t i = 0;
  while (i < text.size()) {
    const std::uint32_t cp = next_codepoint(text, i);
    if (cp == 0) break;
    const GlyphInfo& g = impl_->ensure_glyph(at, cp);
    if (g.w > 0 && g.h > 0) {
      TexturedQuad q;
      q.dst = Rect{cx + g.xoff*glyph_scale, baseline + g.yoff*glyph_scale,
                   float(g.w)*glyph_scale, float(g.h)*glyph_scale};
      q.uv = Rect{float(g.x), float(g.y), float(g.w), float(g.h)};
      quads.push_back(q);
      if (quads.size() > kMaxFillRects)
        throw std::runtime_error("font draw exceeds kMaxFillRects");
    }
    cx += g.advance*glyph_scale;
  }
  // Glyphs may have been added after first ensure_tex - re-upload if dropped.
  if (!at.tex || at.owner != &r) tex = impl_->ensure_tex(r, at);
  if (!quads.empty()) r.draw_textured_quads(tex, quads.data(), quads.size(), color);
}

namespace {
Font* g_default_font = nullptr;
}

Font& default_font() {
  if (!g_default_font) throw std::runtime_error("default_font unset; call try_init_default_font/set_default_font");
  return *g_default_font;
}

void set_default_font(Font font) {
  delete g_default_font;
  g_default_font = new Font(std::move(font));
}

bool try_init_default_font() {
  try {
    set_default_font(Font::load_default());
    return true;
  } catch (...) {
    return false;
  }
}

} // namespace saturn
