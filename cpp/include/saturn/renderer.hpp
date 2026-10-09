#pragma once
#include "types.hpp"
#include <cstddef>
namespace saturn {
class Renderer {
public:
  virtual ~Renderer() = default;
  virtual void clear(Color c) = 0;
  virtual void fill_rect(Rect r, Color c, float radius = 0) = 0;
  // Batch solid axis-aligned rects (same color). Default falls back to fill_rect loop.
  virtual void fill_rects(const Rect* rects, std::size_t count, Color c);
  virtual void stroke_rect(Rect r, Color c, float width = 1, float radius = 0) = 0;
  virtual void clip_push(Rect r) = 0;
  virtual void clip_pop() = 0;
  virtual void flip() = 0;
  virtual void on_resize(int w, int h) = 0;
};
}
