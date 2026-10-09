#include "saturn/control.hpp"
#include "saturn/page.hpp"
#include "saturn/limits.hpp"
#include "saturn/renderer.hpp"
#include "bitmap_font.hpp"
#include <cmath>
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
bool Control::hit_test(float x, float y) const {
  return x >= rect_.x && y >= rect_.y && x < rect_.x + rect_.w && y < rect_.y + rect_.h;
}
void Control::on_pointer(const PointerEvent&) {}

ColorBox::ColorBox(Color color, ControlOptions opt) : Control(std::move(opt)), color_(color) {}
void ColorBox::paint(Renderer& r) {
  if (!opt_.visible) return;
  r.fill_rect(rect_, color_, 0);
  Control::paint(r);
}

Text::Text(std::string value, Color color, ControlOptions opt)
  : Control(std::move(opt)), value_(std::move(value)), color_(color) {
  if (value_.size() > kMaxTextBytes) value_.resize(kMaxTextBytes);
}
void Text::set_value(std::string value) {
  if (value.size() > kMaxTextBytes) value.resize(kMaxTextBytes);
  value_ = std::move(value);
  if (page_) page_->update();
}
const std::string& Text::value() const { return value_; }
Size Text::intrinsic(OptionalSize max_w, OptionalSize) const {
  if (opt_.width || opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  Size s = bitmap_font::measure(value_);
  if (max_w && s.w > *max_w) s.w = *max_w;
  return s;
}
void Text::paint(Renderer& r) {
  if (!opt_.visible) return;
  bitmap_font::draw(r, rect_.x, rect_.y, value_, color_);
}

FilledButton::FilledButton(std::string label, std::function<void()> on_click, ControlOptions opt)
  : Control(std::move(opt)), label_(std::move(label)), on_click_(std::move(on_click)) {
  if (label_.size() > kMaxTextBytes) label_.resize(kMaxTextBytes);
}
void FilledButton::set_corner_radius(float radius) {
  if (!std::isfinite(radius) || radius < 0.f) radius = 0.f;
  if (radius > kMaxCornerRadius) radius = kMaxCornerRadius;
  corner_radius_ = radius;
  if (page_) page_->update();
}
float FilledButton::corner_radius() const { return corner_radius_; }
Size FilledButton::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width || opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  Size text = bitmap_font::measure(label_);
  Size s{text.w + 32.f, text.h + 24.f};
  if (max_w && s.w > *max_w) s.w = *max_w;
  if (max_h && s.h > *max_h) s.h = *max_h;
  return s;
}
void FilledButton::paint(Renderer& r) {
  if (!opt_.visible) return;
  Color bg = pressed_ ? Color{0x37, 0x30, 0xa3, 0xff} : Color{0x4f, 0x46, 0xe5, 0xff};
  r.fill_rect(rect_, bg, corner_radius_);
  // Subtle inside stroke; same radius so SDF fill/stroke share corners.
  Color border = pressed_ ? Color{0x2e, 0x28, 0x8a, 0xff} : Color{0x63, 0x5b, 0xff, 0xff};
  r.stroke_rect(rect_, border, 1.f, corner_radius_);
  Size text = bitmap_font::measure(label_);
  float tx = rect_.x + (rect_.w - text.w) * 0.5f;
  float ty = rect_.y + (rect_.h - text.h) * 0.5f;
  bitmap_font::draw(r, tx, ty, label_, Color{0xff, 0xff, 0xff, 0xff});
}
bool FilledButton::hit_test(float x, float y) const {
  return Control::hit_test(x, y);
}
void FilledButton::on_pointer(const PointerEvent& e) {
  if (!opt_.visible || opt_.disabled) return;
  if (e.down && hit_test(e.x, e.y)) pressed_ = true;
  if (e.up) {
    bool inside = hit_test(e.x, e.y);
    if (pressed_ && inside && on_click_) on_click_();
    pressed_ = false;
  }
}
}
