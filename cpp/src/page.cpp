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
bool Page::layout_dirty() const { return layout_dirty_; }
void Page::layout(float width, float height, float padding, float gap) {
  if (!(width > 0) || !(height > 0)) {
    layout_dirty_ = false; // avoid per-frame spin on invalid size
    return;
  }
  if (width > kMaxLayoutDim) width = float(kMaxLayoutDim);
  if (height > kMaxLayoutDim) height = float(kMaxLayoutDim);
  if (padding < 0) padding = 0;
  if (gap < 0) gap = 0;
  set_rect(Rect{0, 0, width, height});
  float inner_w = width - padding * 2.f;
  if (inner_w < 0) inner_w = 0;
  float y = padding;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic(inner_w, {});
    if (s.w > inner_w) s.w = inner_w;
    child->set_rect(Rect{padding, y, s.w, s.h});
    y += s.h + gap;
  }
  layout_dirty_ = false;
}
void Page::paint(Renderer& r) {
  Control::paint(r);
}
}
