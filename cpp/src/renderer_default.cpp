#include "saturn/renderer.hpp"
#include "saturn/limits.hpp"
#include <cmath>
#include <stdexcept>
namespace saturn {
void Renderer::fill_rects(const Rect* rects, std::size_t count, Color c) {
  if (count > kMaxFillRects)
    throw std::runtime_error("fill_rects exceeds kMaxFillRects");
  if (!rects) return;
  for (std::size_t i = 0; i < count; ++i) fill_rect(rects[i], c, 0);
}

void* Renderer::create_texture_rgba8(int, int, const std::uint8_t*) { return nullptr; }
void Renderer::destroy_texture(void*) {}
void Renderer::draw_textured_quads(void*, const TexturedQuad*, std::size_t count, Color, float radius) {
  if (count > kMaxFillRects)
    throw std::runtime_error("draw_textured_quads exceeds kMaxFillRects");
  if (!std::isfinite(radius))
    throw std::invalid_argument("draw_textured_quads radius must be finite");
}
bool Renderer::read_pixels_rgba(std::vector<std::uint8_t>*, int*, int*) { return false; }

void Renderer::stroke_arc(float cx, float cy, float outer_radius,
                          float start_rad, float sweep_rad, Color, float width) {
  if (!std::isfinite(cx) || !std::isfinite(cy) || !std::isfinite(outer_radius) ||
      !std::isfinite(start_rad) || !std::isfinite(sweep_rad) || !std::isfinite(width))
    throw std::invalid_argument("stroke_arc args must be finite");
  // Default: no GPU path (OpenGL overrides).
  (void)outer_radius;
  (void)width;
}

}
