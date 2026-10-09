#include "saturn/control.hpp"
#include "saturn/limits.hpp"
#include "saturn/renderer.hpp"
namespace saturn {
Control::Control(ControlOptions opt) : opt_(std::move(opt)) {}
void Control::set_options(ControlOptions opt) { opt_ = std::move(opt); }
const ControlOptions& Control::options() const { return opt_; }
void Control::set_rect(Rect rect) { rect_ = rect; }
Rect Control::rect() const { return rect_; }
Size Control::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  float w = opt_.width.value_or(max_w.value_or(0));
  float h = opt_.height.value_or(max_h.value_or(0));
  if (w > kMaxLayoutDim) w = static_cast<float>(kMaxLayoutDim);
  if (h > kMaxLayoutDim) h = static_cast<float>(kMaxLayoutDim);
  if (w < 0) w = 0; if (h < 0) h = 0;
  return {w, h};
}
void Control::paint(Renderer& r) {
  for (auto& child : children_) {
    if (child && child->opt_.visible) child->paint(r);
  }
}

ColorBox::ColorBox(Color color, ControlOptions opt) : Control(std::move(opt)), color_(color) {}
void ColorBox::paint(Renderer& r) {
  if (!opt_.visible) return;
  r.fill_rect(rect_, color_, 0);
  Control::paint(r);
}
}
