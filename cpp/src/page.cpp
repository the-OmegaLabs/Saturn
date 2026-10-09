#include "saturn/page.hpp"
#include "saturn/limits.hpp"
#include "saturn/renderer.hpp"
#include <stdexcept>
namespace saturn {
Page::Page() : Control({}) {}
void Page::set_title(std::string title) {
  if (title.size() > kMaxTextBytes) title.resize(kMaxTextBytes);
  title_ = std::move(title);
}
const std::string& Page::title() const { return title_; }
void Page::add(std::unique_ptr<Control> child) {
  if (!child) return;
  if (children_.size() >= kMaxChildren) throw std::runtime_error("too many children");
  child->attach(this, this);
  children_.push_back(std::move(child));
  layout_dirty_ = true;
}
void Page::update() { layout_dirty_ = true; }
void Page::layout(float width, float height) {
  if (width > kMaxLayoutDim) width = float(kMaxLayoutDim);
  if (height > kMaxLayoutDim) height = float(kMaxLayoutDim);
  set_rect(Rect{0, 0, width, height});
  float y = 40.f;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic(width - 80.f, {});
    child->set_rect(Rect{40.f, y, s.w, s.h});
    y += s.h + 16.f;
  }
  layout_dirty_ = false;
}
void Page::paint(Renderer& r) {
  Control::paint(r);
}
}
