#pragma once
#include "types.hpp"
#include <cstddef>
#include <cstdint>
#include <vector>
namespace saturn {
class Renderer {
public:
  virtual ~Renderer() = default;
  virtual void clear(Color c) = 0;
  virtual void fill_rect(Rect r, Color c, float radius = 0) = 0;
  // Batch solid axis-aligned rects (same color). Default falls back to fill_rect loop.
  // Throws if count > kMaxFillRects.
  virtual void fill_rects(const Rect* rects, std::size_t count, Color c);
  virtual void stroke_rect(Rect r, Color c, float width = 1, float radius = 0) = 0;
  virtual void clip_push(Rect r) = 0;
  virtual void clip_pop() = 0;
  virtual void flip() = 0;
  virtual void on_resize(int w, int h) = 0;

  // Optional GPU textures (OpenGL owns). Defaults: create->nullptr, destroy/draw no-op.
  virtual void* create_texture_rgba8(int w, int h, const std::uint8_t* rgba);
  virtual void destroy_texture(void* tex);
  // uv in TexturedQuad is pixel-space of the texture. Throws if count > kMaxFillRects.
  // Optional corner radius (SDF mask, same caps as fill_rect). radius<=0 = sharp.
  // Non-finite radius throws. When radius>0, quads are drawn one-by-one (per-dst SDF);
  // OpenGL path throws if uRadius / glUniform1f is unavailable (no silent sharp).
  virtual void draw_textured_quads(void* tex, const TexturedQuad* quads, std::size_t count,
                                   Color tint, float radius = 0);

  // Read back RGBA8 framebuffer (origin top-left). out sized w*h*4.
  // Returns false if unsupported. Throws if w*h > kMaxScreenshotPixels.
  virtual bool read_pixels_rgba(std::vector<std::uint8_t>* out, int* out_w, int* out_h);
};
}
