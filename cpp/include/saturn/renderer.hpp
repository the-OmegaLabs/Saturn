#pragma once
#include "types.hpp"
namespace saturn {
// Owns GL context lifetime relative to Window. Caller: App.
class Renderer {
public:
  virtual ~Renderer() = default;
  virtual void clear(Color c) = 0;
  virtual void fill_rect(Rect r, Color c, float radius = 0) = 0;
  virtual void stroke_rect(Rect r, Color c, float width = 1, float radius = 0) = 0;
  virtual void clip_push(Rect r) = 0;
  virtual void clip_pop() = 0;
  virtual void flip() = 0;
  virtual void on_resize(int w, int h) = 0;
};
}
