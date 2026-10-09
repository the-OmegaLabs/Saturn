#include "saturn/control.hpp"
#include "saturn/page.hpp"
#include "saturn/limits.hpp"
#include "saturn/renderer.hpp"
#include "bitmap_font.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace saturn {
namespace {
float clamp_spacing(float spacing) {
  if (!std::isfinite(spacing) || spacing < 0.f) return 0.f;
  if (spacing > float(kMaxLayoutDim)) return float(kMaxLayoutDim);
  return spacing;
}
float effective_corner_radius(float radius, float w, float h) {
  float rad = radius;
  if (!std::isfinite(rad) || rad < 0.f) rad = 0.f;
  if (rad > kMaxCornerRadius) rad = kMaxCornerRadius;
  float half_min = 0.5f * (std::min)(w, h);
  if (rad > half_min) rad = half_min;
  return rad;
}
} // namespace

Control::Control(ControlOptions opt) : opt_(std::move(opt)) {}
void Control::set_options(ControlOptions opt) { opt_ = std::move(opt); }
const ControlOptions& Control::options() const { return opt_; }
void Control::set_rect(Rect rect) { rect_ = rect; }
Rect Control::rect() const { return rect_; }
void Control::attach(Page* page, Control* parent) {
  page_ = page;
  parent_ = parent;
  for (auto& c : children_) {
    if (c) c->attach(page, this);
  }
}
void Control::add_child(std::unique_ptr<Control> child) {
  if (!child) return;
  if (children_.size() >= kMaxChildren) throw std::runtime_error("too many children");
  child->attach(page_, this);
  children_.push_back(std::move(child));
  if (page_) page_->update();
}
Size Control::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  float w = opt_.width.value_or(max_w.value_or(0));
  float h = opt_.height.value_or(max_h.value_or(0));
  if (w > kMaxLayoutDim) w = static_cast<float>(kMaxLayoutDim);
  if (h > kMaxLayoutDim) h = static_cast<float>(kMaxLayoutDim);
  if (w < 0) w = 0; if (h < 0) h = 0;
  return {w, h};
}
void Control::layout() {
  for (auto& child : children_) {
    if (child) child->layout();
  }
}
void Control::paint(Renderer& r) {
  for (auto& child : children_) {
    if (child && child->opt_.visible) child->paint(r);
  }
}
bool Control::hit_test(float x, float y) const {
  return x >= rect_.x && y >= rect_.y && x < rect_.x + rect_.w && y < rect_.y + rect_.h;
}
Control* Control::hit_target(float x, float y) {
  for (auto it = children_.rbegin(); it != children_.rend(); ++it) {
    Control* c = it->get();
    if (!c || !c->opt_.visible || c->opt_.disabled) continue;
    if (Control* t = c->hit_target(x, y)) return t;
  }
  if (hit_test(x, y)) return this;
  return nullptr;
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
  if (!(x >= rect_.x && y >= rect_.y && x < rect_.x + rect_.w && y < rect_.y + rect_.h))
    return false;
  float rad = effective_corner_radius(corner_radius_, rect_.w, rect_.h);
  if (rad <= 0.f) return true;
  float lx = x - rect_.x;
  float ly = y - rect_.y;
  float rw = rect_.w;
  float rh = rect_.h;
  // Center strips (not in a corner pocket) are inside.
  if (lx >= rad && lx <= rw - rad) return true;
  if (ly >= rad && ly <= rh - rad) return true;
  float cx = (lx < rad) ? rad : (rw - rad);
  float cy = (ly < rad) ? rad : (rh - rad);
  float dx = lx - cx;
  float dy = ly - cy;
  return dx * dx + dy * dy <= rad * rad;
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

Column::Column(float spacing, ControlOptions opt)
  : Control(std::move(opt)), spacing_(clamp_spacing(spacing)) {}
void Column::add(std::unique_ptr<Control> child) { add_child(std::move(child)); }
float Column::spacing() const { return spacing_; }
Size Column::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width && opt_.height) return Control::intrinsic(max_w, max_h);
  float w = 0.f;
  float h = 0.f;
  std::size_t n_vis = 0;
  for (const auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic(max_w, {});
    if (s.w > w) w = s.w;
    h += s.h;
    ++n_vis;
  }
  if (n_vis > 1) h += spacing_ * float(n_vis - 1);
  if (opt_.width) w = *opt_.width;
  if (opt_.height) h = *opt_.height;
  if (max_w && w > *max_w) w = *max_w;
  if (max_h && h > *max_h) h = *max_h;
  if (w > float(kMaxLayoutDim)) w = float(kMaxLayoutDim);
  if (h > float(kMaxLayoutDim)) h = float(kMaxLayoutDim);
  if (w < 0) w = 0;
  if (h < 0) h = 0;
  return {w, h};
}
void Column::layout() {
  float y = rect_.y;
  const float x = rect_.x;
  const float inner_w = rect_.w > 0.f ? rect_.w : 0.f;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic(inner_w, {});
    if (s.w > inner_w) s.w = inner_w;
    child->set_rect(Rect{x, y, s.w, s.h});
    child->layout();
    y += s.h + spacing_;
  }
}

Row::Row(float spacing, ControlOptions opt)
  : Control(std::move(opt)), spacing_(clamp_spacing(spacing)) {}
void Row::add(std::unique_ptr<Control> child) { add_child(std::move(child)); }
float Row::spacing() const { return spacing_; }
Size Row::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width && opt_.height) return Control::intrinsic(max_w, max_h);
  float w = 0.f;
  float h = 0.f;
  std::size_t n_vis = 0;
  for (const auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic({}, max_h);
    if (s.h > h) h = s.h;
    w += s.w;
    ++n_vis;
  }
  if (n_vis > 1) w += spacing_ * float(n_vis - 1);
  if (opt_.width) w = *opt_.width;
  if (opt_.height) h = *opt_.height;
  if (max_w && w > *max_w) w = *max_w;
  if (max_h && h > *max_h) h = *max_h;
  if (w > float(kMaxLayoutDim)) w = float(kMaxLayoutDim);
  if (h > float(kMaxLayoutDim)) h = float(kMaxLayoutDim);
  if (w < 0) w = 0;
  if (h < 0) h = 0;
  return {w, h};
}
void Row::layout() {
  float x = rect_.x;
  const float y = rect_.y;
  const float inner_h = rect_.h > 0.f ? rect_.h : 0.f;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic({}, inner_h);
    if (s.h > inner_h && inner_h > 0.f) s.h = inner_h;
    child->set_rect(Rect{x, y, s.w, s.h});
    child->layout();
    x += s.w + spacing_;
  }
}

Container::Container(ControlOptions opt) : Control(std::move(opt)) {}
void Container::set_bgcolor(Color c) { bgcolor_ = c; has_bg_ = true; if (page_) page_->update(); }
void Container::set_padding(float pad) {
  if (!std::isfinite(pad) || pad < 0.f) pad = 0.f;
  if (pad > float(kMaxLayoutDim)) pad = float(kMaxLayoutDim);
  padding_ = pad;
  if (page_) page_->update();
}
void Container::set_corner_radius(float radius) {
  if (!std::isfinite(radius) || radius < 0.f) radius = 0.f;
  if (radius > kMaxCornerRadius) radius = kMaxCornerRadius;
  corner_radius_ = radius;
  if (page_) page_->update();
}
void Container::add(std::unique_ptr<Control> child) { add_child(std::move(child)); }
Size Container::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width || opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  float pad2 = padding_ * 2.f;
  OptionalSize child_max_w = max_w ? OptionalSize(*max_w - pad2) : OptionalSize{};
  OptionalSize child_max_h = max_h ? OptionalSize(*max_h - pad2) : OptionalSize{};
  float w = 0.f, h = 0.f;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic(child_max_w, child_max_h);
    if (s.w > w) w = s.w;
    if (s.h > h) h = s.h;
  }
  w += pad2; h += pad2;
  if (w < 0) w = 0; if (h < 0) h = 0;
  if (w > float(kMaxLayoutDim)) w = float(kMaxLayoutDim);
  if (h > float(kMaxLayoutDim)) h = float(kMaxLayoutDim);
  return {w, h};
}
void Container::layout() {
  float inner_x = rect_.x + padding_;
  float inner_y = rect_.y + padding_;
  float inner_w = rect_.w - padding_ * 2.f;
  float inner_h = rect_.h - padding_ * 2.f;
  if (inner_w < 0) inner_w = 0;
  if (inner_h < 0) inner_h = 0;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic(inner_w, inner_h);
    if (s.w > inner_w) s.w = inner_w;
    if (s.h > inner_h) s.h = inner_h;
    child->set_rect(Rect{inner_x, inner_y, s.w, s.h});
    child->layout();
  }
}
void Container::paint(Renderer& r) {
  if (!opt_.visible) return;
  if (has_bg_ && bgcolor_.a) r.fill_rect(rect_, bgcolor_, corner_radius_);
  r.clip_push(rect_);
  Control::paint(r);
  r.clip_pop();
}
bool Container::hit_test(float x, float y) const {
  float rad = effective_corner_radius(corner_radius_, rect_.w, rect_.h);
  if (!(x >= rect_.x && y >= rect_.y && x < rect_.x + rect_.w && y < rect_.y + rect_.h))
    return false;
  if (rad <= 0.f) return true;
  float lx = x - rect_.x, ly = y - rect_.y, rw = rect_.w, rh = rect_.h;
  if (lx >= rad && lx <= rw - rad) return true;
  if (ly >= rad && ly <= rh - rad) return true;
  float cx = (lx < rad) ? rad : (rw - rad);
  float cy = (ly < rad) ? rad : (rh - rad);
  float dx = lx - cx, dy = ly - cy;
  return dx * dx + dy * dy <= rad * rad;
}
}
