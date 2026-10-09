#include "saturn/renderer.hpp"
namespace saturn {
void Renderer::fill_rects(const Rect* rects, std::size_t count, Color c) {
  if (!rects) return;
  for (std::size_t i = 0; i < count; ++i) fill_rect(rects[i], c, 0);
}
}
