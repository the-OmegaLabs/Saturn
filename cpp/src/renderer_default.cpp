#include "saturn/renderer.hpp"
#include "saturn/limits.hpp"
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
void Renderer::draw_textured_quads(void*, const TexturedQuad*, std::size_t count, Color) {
  if (count > kMaxFillRects)
    throw std::runtime_error("draw_textured_quads exceeds kMaxFillRects");
}
}
