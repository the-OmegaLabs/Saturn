#include "saturn/control.hpp"
#include "saturn/colors.hpp"
#include "saturn/page.hpp"
#include "saturn/limits.hpp"
#include "saturn/renderer.hpp"
#include "saturn/font.hpp"
#include "saturn/geometry.hpp"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <vector>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_NO_STDIO
// Must match saturn::kMaxImageDecodeDim (limits.hpp). Set before stb include.
#define STBI_MAX_DIMENSIONS 4096
#include "stb_image.h"

namespace saturn {
static_assert(STBI_MAX_DIMENSIONS == kMaxImageDecodeDim,
              "STBI_MAX_DIMENSIONS must equal kMaxImageDecodeDim");
namespace {
constexpr float kUiFontPx = 16.f;
// M3 button metrics (saturn/widgets/buttons.py non-expressive).
constexpr float kLabelFontPx = 14.f;
constexpr float kPadH = 24.f;
constexpr float kHeight = 40.f;
constexpr float kIconGap = 8.f;
constexpr float kLeadingIconPx = 18.f;
constexpr float kStrokeW = 1.f;

float clamp_spacing(float spacing) {
  if (!std::isfinite(spacing) || spacing < 0.f) return 0.f;
  if (spacing > float(kMaxLayoutDim)) return float(kMaxLayoutDim);
  return spacing;
}
float clamp_radius(float radius) {
  if (!std::isfinite(radius) || radius < 0.f) return 0.f;
  if (radius > kMaxCornerRadius) return kMaxCornerRadius;
  return radius;
}
// Offset of child along cross axis inside parent cross size.
float cross_offset(CrossAxisAlignment a, float child_cross, float parent_cross) {
  if (parent_cross <= 0.f || child_cross >= parent_cross) return 0.f;
  switch (a) {
    case CrossAxisAlignment::End:
      return parent_cross - child_cross;
    case CrossAxisAlignment::Center:
      return (parent_cross - child_cross) * 0.5f;
    case CrossAxisAlignment::Start:
    case CrossAxisAlignment::Stretch:
    default:
      return 0.f;
  }
}

Size measure_button_label(const std::string& label, const std::string& icon,
                          OptionalSize max_w, OptionalSize max_h) {
  Size text = default_font().measure(label, kLabelFontPx);
  float w = text.w + 2.f * kPadH;
  if (!icon.empty()) {
    Size ic = default_font().measure(icon, kLeadingIconPx);
    w += ic.w + kIconGap;
  }
  Size s{w, kHeight};
  if (max_w && s.w > *max_w) s.w = *max_w;
  if (max_h && s.h > *max_h) s.h = *max_h;
  return s;
}

void paint_centered_label(Renderer& r, const Rect& rect, const std::string& label,
                          const std::string& icon, Color fg) {
  Size text = default_font().measure(label, kLabelFontPx);
  float content_w = text.w;
  Size ic{};
  if (!icon.empty()) {
    ic = default_font().measure(icon, kLeadingIconPx);
    content_w += ic.w + kIconGap;
  }
  float x = rect.x + (rect.w - content_w) * 0.5f;
  float ty = rect.y + (rect.h - text.h) * 0.5f;
  if (!icon.empty()) {
    float iy = rect.y + (rect.h - ic.h) * 0.5f;
    default_font().draw(r, x, iy, icon, fg, kLeadingIconPx);
    x += ic.w + kIconGap;
  }
  default_font().draw(r, x, ty, label, fg, kLabelFontPx);
}

std::vector<std::uint8_t> read_file_capped(const std::string& path, std::size_t max_bytes) {
  if (path.size() > kMaxPathBytes)
    throw std::invalid_argument("path exceeds kMaxPathBytes");
  std::ifstream in(path, std::ios::binary | std::ios::ate);
  if (!in) throw std::runtime_error("file open failed: " + path);
  const auto end = in.tellg();
  if (end < 0) throw std::runtime_error("file size failed: " + path);
  const auto sz = static_cast<std::uint64_t>(end);
  if (sz == 0 || sz > max_bytes)
    throw std::runtime_error("file size rejected: " + path);
  in.seekg(0);
  std::vector<std::uint8_t> buf(static_cast<std::size_t>(sz));
  if (!in.read(reinterpret_cast<char*>(buf.data()), static_cast<std::streamsize>(buf.size())))
    throw std::runtime_error("file read failed: " + path);
  return buf;
}

std::string resolve_asset_path(const std::string& path) {
  if (path.empty()) return path;
  // Absolute or already-openable path wins.
  {
    std::ifstream probe(path, std::ios::binary);
    if (probe) return path;
  }
  std::vector<std::string> candidates;
  if (const char* base = std::getenv("SATURN_ASSETS_DIR")) {
    std::string b(base);
    if (!b.empty() && b.back() != '/') b.push_back('/');
    candidates.push_back(b + path);
  }
  candidates.push_back(std::string("assets/") + path);
  candidates.push_back(std::string("cpp/assets/") + path);
  candidates.push_back(std::string(".static/") + path);
  // Also try path as relative under assets if it already starts with assets/.
  for (const auto& c : candidates) {
    std::ifstream probe(c, std::ios::binary);
    if (probe) return c;
  }
  return path; // let loader report the original
}

} // namespace

Control::Control(ControlOptions opt) : opt_(std::move(opt)) {}
void Control::set_options(ControlOptions opt) { opt_ = std::move(opt); }
const ControlOptions& Control::options() const { return opt_; }
void Control::set_expand(bool expand) {
  opt_.expand = expand;
  if (page_) page_->update();
}
bool Control::expand() const { return opt_.expand; }
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

Text::Text(std::string value, Color color, float size, ControlOptions opt)
  : Control(std::move(opt)), value_(std::move(value)), color_(color) {
  if (value_.size() > kMaxTextBytes) value_.resize(kMaxTextBytes);
  set_size(size);
}
void Text::set_value(std::string value) {
  if (value.size() > kMaxTextBytes) value.resize(kMaxTextBytes);
  value_ = std::move(value);
  if (page_) page_->update();
}
const std::string& Text::value() const { return value_; }
void Text::set_size(float px) {
  if (!std::isfinite(px)) px = kUiFontPx;
  if (px < kMinFontPx) px = kMinFontPx;
  if (px > kMaxFontPx) px = kMaxFontPx;
  size_ = px;
  if (page_) page_->update();
}
float Text::size() const { return size_; }
Size Text::intrinsic(OptionalSize max_w, OptionalSize) const {
  if (opt_.width || opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  Size s = default_font().measure(value_, size_);
  if (max_w && s.w > *max_w) s.w = *max_w;
  return s;
}
void Text::paint(Renderer& r) {
  if (!opt_.visible) return;
  default_font().draw(r, rect_.x, rect_.y, value_, color_, size_);
}

FilledButton::FilledButton(std::string label, std::function<void()> on_click, ControlOptions opt)
  : Control(std::move(opt)), label_(std::move(label)), on_click_(std::move(on_click)) {
  if (label_.size() > kMaxTextBytes) label_.resize(kMaxTextBytes);
}
void FilledButton::set_corner_radius(float radius) {
  corner_radius_ = clamp_radius(radius);
  if (page_) page_->update();
}
float FilledButton::corner_radius() const { return corner_radius_; }
Size FilledButton::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width || opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  return measure_button_label(label_, "", max_w, max_h);
}
void FilledButton::paint(Renderer& r) {
  if (!opt_.visible) return;
  // Idle PRIMARY; pressed PRIMARY_CONTAINER (theme token — no hand-written RGB).
  Color bg = pressed_ ? colors::kPrimaryContainer : colors::kPrimary;
  Color fg = pressed_ ? colors::kOnPrimaryContainer : colors::kOnPrimary;
  r.fill_rect(rect_, bg, corner_radius_);
  paint_centered_label(r, rect_, label_, "", fg);
}
bool FilledButton::hit_test(float x, float y) const {
  return hit_round_rect(x, y, rect_, corner_radius_);
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

ElevatedButton::ElevatedButton(std::string label, std::function<void()> on_click,
                               std::string icon, ControlOptions opt)
  : Control(std::move(opt)), label_(std::move(label)), icon_(std::move(icon)),
    on_click_(std::move(on_click)) {
  if (label_.size() > kMaxTextBytes) label_.resize(kMaxTextBytes);
  if (icon_.size() > kMaxTextBytes) icon_.resize(kMaxTextBytes);
}
void ElevatedButton::set_corner_radius(float radius) {
  corner_radius_ = clamp_radius(radius);
  if (page_) page_->update();
}
float ElevatedButton::corner_radius() const { return corner_radius_; }
Size ElevatedButton::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width || opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  return measure_button_label(label_, icon_, max_w, max_h);
}
void ElevatedButton::paint(Renderer& r) {
  if (!opt_.visible) return;
  // Elev look via fill: SURFACE_CONTAINER_LOW idle; pressed SURFACE_CONTAINER_HIGH.
  Color bg = pressed_ ? colors::kSurfaceContainerHigh : colors::kSurfaceContainerLow;
  r.fill_rect(rect_, bg, corner_radius_);
  paint_centered_label(r, rect_, label_, icon_, colors::kPrimary);
}
bool ElevatedButton::hit_test(float x, float y) const {
  return hit_round_rect(x, y, rect_, corner_radius_);
}
void ElevatedButton::on_pointer(const PointerEvent& e) {
  if (!opt_.visible || opt_.disabled) return;
  if (e.down && hit_test(e.x, e.y)) pressed_ = true;
  if (e.up) {
    bool inside = hit_test(e.x, e.y);
    if (pressed_ && inside && on_click_) on_click_();
    pressed_ = false;
  }
}

OutlinedButton::OutlinedButton(std::string label, std::function<void()> on_click,
                               ControlOptions opt)
  : Control(std::move(opt)), label_(std::move(label)), on_click_(std::move(on_click)) {
  if (label_.size() > kMaxTextBytes) label_.resize(kMaxTextBytes);
}
void OutlinedButton::set_corner_radius(float radius) {
  corner_radius_ = clamp_radius(radius);
  if (page_) page_->update();
}
float OutlinedButton::corner_radius() const { return corner_radius_; }
Size OutlinedButton::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width || opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  return measure_button_label(label_, "", max_w, max_h);
}
void OutlinedButton::paint(Renderer& r) {
  if (!opt_.visible) return;
  if (pressed_) {
    r.fill_rect(rect_, colors::kSurfaceContainer, corner_radius_);
  }
  r.stroke_rect(rect_, colors::kOutlineVariant, kStrokeW, corner_radius_);
  paint_centered_label(r, rect_, label_, "", colors::kOnSurfaceVariant);
}
bool OutlinedButton::hit_test(float x, float y) const {
  return hit_round_rect(x, y, rect_, corner_radius_);
}
void OutlinedButton::on_pointer(const PointerEvent& e) {
  if (!opt_.visible || opt_.disabled) return;
  if (e.down && hit_test(e.x, e.y)) pressed_ = true;
  if (e.up) {
    bool inside = hit_test(e.x, e.y);
    if (pressed_ && inside && on_click_) on_click_();
    pressed_ = false;
  }
}

IconButton::IconButton(std::string icon, std::function<void()> on_click, ControlOptions opt)
  : Control(std::move(opt)), icon_(std::move(icon)), on_click_(std::move(on_click)) {
  if (icon_.size() > kMaxTextBytes) icon_.resize(kMaxTextBytes);
  if (!opt_.width) opt_.width = kSide;
  if (!opt_.height) opt_.height = kSide;
}
Size IconButton::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  Size s{opt_.width.value_or(kSide), opt_.height.value_or(kSide)};
  if (max_w && s.w > *max_w) s.w = *max_w;
  if (max_h && s.h > *max_h) s.h = *max_h;
  return s;
}
void IconButton::paint(Renderer& r) {
  if (!opt_.visible) return;
  const float radius = std::min(rect_.w, rect_.h) * 0.5f;
  if (pressed_) {
    r.fill_rect(rect_, colors::kPrimaryContainer, radius);
  }
  Size ic = default_font().measure(icon_, kIconPx);
  float tx = rect_.x + (rect_.w - ic.w) * 0.5f;
  float ty = rect_.y + (rect_.h - ic.h) * 0.5f;
  Color fg = pressed_ ? colors::kOnPrimaryContainer : colors::kOnSurface;
  default_font().draw(r, tx, ty, icon_, fg, kIconPx);
}
bool IconButton::hit_test(float x, float y) const {
  const float radius = std::min(rect_.w, rect_.h) * 0.5f;
  return hit_round_rect(x, y, rect_, radius);
}
void IconButton::on_pointer(const PointerEvent& e) {
  if (!opt_.visible || opt_.disabled) return;
  if (e.down && hit_test(e.x, e.y)) pressed_ = true;
  if (e.up) {
    bool inside = hit_test(e.x, e.y);
    if (pressed_ && inside && on_click_) on_click_();
    pressed_ = false;
  }
}

Image::Image(std::string path, ControlOptions opt)
  : Control(std::move(opt)), path_(std::move(path)) {
  if (path_.empty())
    throw std::invalid_argument("Image path is empty");
  if (path_.size() > kMaxPathBytes)
    throw std::invalid_argument("Image path exceeds kMaxPathBytes");
}
Image::~Image() { release_texture(); }
void Image::set_tint(Color c) {
  has_tint_ = true;
  tint_ = c;
  if (page_) page_->update();
}
void Image::clear_tint() {
  has_tint_ = false;
  tint_ = Color{255, 255, 255, 255};
  if (page_) page_->update();
}
bool Image::loaded() const { return load_ok_; }
void Image::release_texture() {
  if (tex_ && tex_r_) {
    tex_r_->destroy_texture(tex_);
  }
  tex_ = nullptr;
  tex_r_ = nullptr;
}
void Image::ensure_loaded() const {
  if (load_ok_) return;
  if (tried_load_)
    throw std::runtime_error("image load previously failed: " + path_);
  tried_load_ = true;
  const std::string resolved = resolve_asset_path(path_);
  if (resolved.size() > kMaxPathBytes)
    throw std::invalid_argument("image resolved path exceeds kMaxPathBytes");
  auto file = read_file_capped(resolved, kMaxImageFileBytes);
  int w = 0, h = 0, n = 0;
  stbi_uc* pixels = stbi_load_from_memory(
      file.data(), static_cast<int>(file.size()), &w, &h, &n, 4);
  if (!pixels || w <= 0 || h <= 0) {
    if (pixels) stbi_image_free(pixels);
    throw std::runtime_error("image decode failed: " + path_);
  }
  const auto uw = static_cast<std::size_t>(w);
  const auto uh = static_cast<std::size_t>(h);
  if (w > kMaxImageDecodeDim || h > kMaxImageDecodeDim ||
      uw > kMaxLayoutDim || uh > kMaxLayoutDim ||
      uw * uh > kMaxScreenshotPixels) {
    stbi_image_free(pixels);
    throw std::runtime_error("image dimensions exceed caps: " + path_);
  }
  rgba_.assign(pixels, pixels + uw * uh * 4u);
  stbi_image_free(pixels);
  src_w_ = w;
  src_h_ = h;
  load_ok_ = true;
}
void Image::ensure_texture(Renderer& r) {
  if (!load_ok_ || rgba_.empty()) return;
  if (tex_ && tex_r_ == &r) return;
  release_texture();
  tex_ = r.create_texture_rgba8(src_w_, src_h_, rgba_.data());
  if (tex_) tex_r_ = &r;
}
Size Image::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width && opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  ensure_loaded();
  float w = opt_.width.value_or(load_ok_ ? float(src_w_) : 0.f);
  float h = opt_.height.value_or(load_ok_ ? float(src_h_) : 0.f);
  if (!opt_.width && !opt_.height && load_ok_) {
    w = float(src_w_);
    h = float(src_h_);
  } else if (opt_.width && !opt_.height && load_ok_ && src_w_ > 0) {
    h = (*opt_.width) * float(src_h_) / float(src_w_);
  } else if (!opt_.width && opt_.height && load_ok_ && src_h_ > 0) {
    w = (*opt_.height) * float(src_w_) / float(src_h_);
  }
  if (max_w && w > *max_w) w = *max_w;
  if (max_h && h > *max_h) h = *max_h;
  if (w > float(kMaxLayoutDim)) w = float(kMaxLayoutDim);
  if (h > float(kMaxLayoutDim)) h = float(kMaxLayoutDim);
  if (w < 0) w = 0;
  if (h < 0) h = 0;
  return {w, h};
}
void Image::paint(Renderer& r) {
  if (!opt_.visible) return;
  ensure_loaded();
  if (!load_ok_) return;
  ensure_texture(r);
  if (!tex_) return;
  // BoxFit.CONTAIN when both axes are constrained by the laid-out rect.
  float scale = 1.f;
  if (src_w_ > 0 && src_h_ > 0 && rect_.w > 0.f && rect_.h > 0.f) {
    scale = std::min(rect_.w / float(src_w_), rect_.h / float(src_h_));
  }
  float dw = float(src_w_) * scale;
  float dh = float(src_h_) * scale;
  if (dw > float(kMaxLayoutDim)) dw = float(kMaxLayoutDim);
  if (dh > float(kMaxLayoutDim)) dh = float(kMaxLayoutDim);
  Rect dst{
    rect_.x + (rect_.w - dw) * 0.5f,
    rect_.y + (rect_.h - dh) * 0.5f,
    dw, dh};
  TexturedQuad q;
  q.dst = dst;
  q.uv = Rect{0.f, 0.f, float(src_w_), float(src_h_)};
  Color tint = has_tint_ ? tint_ : Color{255, 255, 255, 255};
  r.draw_textured_quads(tex_, &q, 1, tint);
}

Column::Column(float spacing, ControlOptions opt)
  : Control(std::move(opt)), spacing_(clamp_spacing(spacing)) {}
void Column::add(std::unique_ptr<Control> child) { add_child(std::move(child)); }
void Column::set_spacing(float spacing) {
  spacing_ = clamp_spacing(spacing);
  if (page_) page_->update();
}
float Column::spacing() const { return spacing_; }
void Column::set_cross_axis_alignment(CrossAxisAlignment align) {
  cross_align_ = align;
  if (page_) page_->update();
}
CrossAxisAlignment Column::cross_axis_alignment() const { return cross_align_; }
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
  // Main = Y, cross = X. Expand kids share leftover height equally.
  const float inner_w = rect_.w > 0.f ? rect_.w : 0.f;
  const float inner_h = rect_.h > 0.f ? rect_.h : 0.f;
  std::size_t n_vis = 0;
  std::size_t n_expand = 0;
  float fixed_h = 0.f;
  for (const auto& child : children_) {
    if (!child || !child->options().visible) continue;
    ++n_vis;
    if (child->expand()) {
      ++n_expand;
      continue;
    }
    Size s = child->intrinsic(inner_w, {});
    fixed_h += s.h;
  }
  const float gaps = n_vis > 1 ? spacing_ * float(n_vis - 1) : 0.f;
  float leftover = inner_h - fixed_h - gaps;
  if (leftover < 0.f) leftover = 0.f;
  const float expand_share = n_expand > 0 ? leftover / float(n_expand) : 0.f;

  float y = rect_.y;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    float main_h = 0.f;
    float cross_w = 0.f;
    if (child->expand()) {
      main_h = expand_share;
      Size s = child->intrinsic(inner_w, main_h);
      cross_w = s.w;
    } else {
      Size s = child->intrinsic(inner_w, {});
      main_h = s.h;
      cross_w = s.w;
    }
    // Stretch fills cross unless child has an explicit width.
    if (cross_align_ == CrossAxisAlignment::Stretch && !child->options().width) {
      cross_w = inner_w;
    } else if (cross_w > inner_w) {
      cross_w = inner_w;
    }
    if (main_h > float(kMaxLayoutDim)) main_h = float(kMaxLayoutDim);
    if (cross_w > float(kMaxLayoutDim)) cross_w = float(kMaxLayoutDim);
    if (main_h < 0.f) main_h = 0.f;
    if (cross_w < 0.f) cross_w = 0.f;
    const float cx = cross_offset(cross_align_, cross_w, inner_w);
    child->set_rect(Rect{rect_.x + cx, y, cross_w, main_h});
    child->layout();
    y += main_h + spacing_;
  }
}

Row::Row(float spacing, ControlOptions opt)
  : Control(std::move(opt)), spacing_(clamp_spacing(spacing)) {}
void Row::add(std::unique_ptr<Control> child) { add_child(std::move(child)); }
void Row::set_spacing(float spacing) {
  spacing_ = clamp_spacing(spacing);
  if (page_) page_->update();
}
float Row::spacing() const { return spacing_; }
void Row::set_cross_axis_alignment(CrossAxisAlignment align) {
  cross_align_ = align;
  if (page_) page_->update();
}
CrossAxisAlignment Row::cross_axis_alignment() const { return cross_align_; }
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
  // Main = X, cross = Y. Expand kids share leftover width equally.
  const float inner_w = rect_.w > 0.f ? rect_.w : 0.f;
  const float inner_h = rect_.h > 0.f ? rect_.h : 0.f;
  std::size_t n_vis = 0;
  std::size_t n_expand = 0;
  float fixed_w = 0.f;
  for (const auto& child : children_) {
    if (!child || !child->options().visible) continue;
    ++n_vis;
    if (child->expand()) {
      ++n_expand;
      continue;
    }
    Size s = child->intrinsic({}, inner_h);
    fixed_w += s.w;
  }
  const float gaps = n_vis > 1 ? spacing_ * float(n_vis - 1) : 0.f;
  float leftover = inner_w - fixed_w - gaps;
  if (leftover < 0.f) leftover = 0.f;
  const float expand_share = n_expand > 0 ? leftover / float(n_expand) : 0.f;

  float x = rect_.x;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    float main_w = 0.f;
    float cross_h = 0.f;
    if (child->expand()) {
      main_w = expand_share;
      Size s = child->intrinsic(main_w, inner_h);
      cross_h = s.h;
    } else {
      Size s = child->intrinsic({}, inner_h);
      main_w = s.w;
      cross_h = s.h;
    }
    // Stretch fills cross unless child has an explicit height.
    if (cross_align_ == CrossAxisAlignment::Stretch && !child->options().height) {
      cross_h = inner_h;
    } else if (cross_h > inner_h && inner_h > 0.f) {
      cross_h = inner_h;
    }
    if (main_w > float(kMaxLayoutDim)) main_w = float(kMaxLayoutDim);
    if (cross_h > float(kMaxLayoutDim)) cross_h = float(kMaxLayoutDim);
    if (main_w < 0.f) main_w = 0.f;
    if (cross_h < 0.f) cross_h = 0.f;
    const float cy = cross_offset(cross_align_, cross_h, inner_h);
    child->set_rect(Rect{x, rect_.y + cy, main_w, cross_h});
    child->layout();
    x += main_w + spacing_;
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
  float pad2 = padding_ * 2.f;
  // Width-only / height-only: still measure the unset axis from children.
  float fixed_w = opt_.width ? *opt_.width : -1.f;
  float fixed_h = opt_.height ? *opt_.height : -1.f;
  float avail_w = fixed_w >= 0.f ? fixed_w - pad2
                : (max_w ? (*max_w - pad2) : -1.f);
  float avail_h = fixed_h >= 0.f ? fixed_h - pad2
                : (max_h ? (*max_h - pad2) : -1.f);
  OptionalSize child_max_w = avail_w >= 0.f ? OptionalSize(avail_w) : OptionalSize{};
  OptionalSize child_max_h = avail_h >= 0.f ? OptionalSize(avail_h) : OptionalSize{};
  float w = 0.f, h = 0.f;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic(child_max_w, child_max_h);
    if (s.w > w) w = s.w;
    if (s.h > h) h = s.h;
  }
  w += pad2; h += pad2;
  if (fixed_w >= 0.f) w = fixed_w;
  if (fixed_h >= 0.f) h = fixed_h;
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
  return hit_round_rect(x, y, rect_, corner_radius_);
}
}
