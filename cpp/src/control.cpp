#include "saturn/control.hpp"
#include "saturn/colors.hpp"
#include "saturn/page.hpp"
#include "saturn/limits.hpp"
#include "saturn/renderer.hpp"
#include "saturn/font.hpp"
#include "saturn/geometry.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <memory>
#include <vector>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_NO_STDIO
// Must match saturn::kMaxImageDecodeDim (limits.hpp). Set before stb include.
#define STBI_MAX_DIMENSIONS 4096
#include "stb_image.h"
#include "icon_assets.hpp"

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

Size measure_button_label(const std::string& label, bool has_icon,
                          OptionalSize max_w, OptionalSize max_h) {
  Size text = default_font().measure(label, kLabelFontPx);
  float w = text.w + 2.f * kPadH;
  if (has_icon) w += kLeadingIconPx + kIconGap;
  Size s{w, kHeight};
  if (max_w && s.w > *max_w) s.w = *max_w;
  if (max_h && s.h > *max_h) s.h = *max_h;
  return s;
}

void paint_centered_label(Renderer& r, const Rect& rect, const std::string& label,
                          TextureImage* leading, Color fg) {
  Size text = default_font().measure(label, kLabelFontPx);
  float content_w = text.w;
  if (leading) content_w += kLeadingIconPx + kIconGap;
  float x = rect.x + (rect.w - content_w) * 0.5f;
  float ty = rect.y + (rect.h - text.h) * 0.5f;
  if (leading) {
    Rect idst{x, rect.y + (rect.h - kLeadingIconPx) * 0.5f,
              kLeadingIconPx, kLeadingIconPx};
    leading->draw(r, idst, fg);
    x += kLeadingIconPx + kIconGap;
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


// Decode PNG with same caps as Image (path / file bytes / STBI dim / pixel count).
struct DecodedPng {
  std::vector<std::uint8_t> rgba;
  int w = 0;
  int h = 0;
};
DecodedPng decode_png_from_bytes(const std::uint8_t* data, std::size_t len,
                                  const std::string& label) {
  if (!data || len == 0)
    throw std::runtime_error("image bytes empty: " + label);
  if (len > kMaxImageFileBytes)
    throw std::runtime_error("image bytes exceed kMaxImageFileBytes: " + label);
  int w = 0, h = 0, n = 0;
  stbi_uc* pixels = stbi_load_from_memory(
      data, static_cast<int>(len), &w, &h, &n, 4);
  if (!pixels || w <= 0 || h <= 0) {
    if (pixels) stbi_image_free(pixels);
    throw std::runtime_error("image decode failed: " + label);
  }
  const auto uw = static_cast<std::size_t>(w);
  const auto uh = static_cast<std::size_t>(h);
  if (w > kMaxImageDecodeDim || h > kMaxImageDecodeDim ||
      uw > kMaxLayoutDim || uh > kMaxLayoutDim ||
      uw * uh > kMaxScreenshotPixels) {
    stbi_image_free(pixels);
    throw std::runtime_error("image dimensions exceed caps: " + label);
  }
  DecodedPng out;
  out.rgba.assign(pixels, pixels + uw * uh * 4u);
  stbi_image_free(pixels);
  out.w = w;
  out.h = h;
  return out;
}

DecodedPng decode_png_capped(const std::string& path) {
  if (path.empty())
    throw std::invalid_argument("image path is empty");
  if (path.size() > kMaxPathBytes)
    throw std::invalid_argument("image path exceeds kMaxPathBytes");
  // Bundled Material icon bitmaps (also shipped under assets/icons/).
  if (auto emb = icon_assets::find(path.c_str()); emb.data)
    return decode_png_from_bytes(emb.data, emb.len, path);
  const std::string resolved = resolve_asset_path(path);
  if (resolved.size() > kMaxPathBytes)
    throw std::invalid_argument("image resolved path exceeds kMaxPathBytes");
  auto file = read_file_capped(resolved, kMaxImageFileBytes);
  return decode_png_from_bytes(file.data(), file.size(), path);
}

} // namespace

TextureImage::TextureImage(std::string path) : path_(std::move(path)) {
  if (path_.empty())
    throw std::invalid_argument("TextureImage path is empty");
  if (path_.size() > kMaxPathBytes)
    throw std::invalid_argument("TextureImage path exceeds kMaxPathBytes");
}
TextureImage::~TextureImage() { release_texture(); }
void TextureImage::release_texture() {
  if (tex_ && tex_r_) tex_r_->destroy_texture(tex_);
  tex_ = nullptr;
  tex_r_ = nullptr;
}
void TextureImage::ensure_loaded() const {
  if (load_ok_) return;
  if (tried_load_)
    throw std::runtime_error("image load previously failed: " + path_);
  tried_load_ = true;
  DecodedPng dec = decode_png_capped(path_);
  rgba_ = std::move(dec.rgba);
  src_w_ = dec.w;
  src_h_ = dec.h;
  load_ok_ = true;
}
void* TextureImage::ensure_texture(Renderer& r) {
  ensure_loaded();
  if (!load_ok_ || rgba_.empty())
    throw std::runtime_error("image not loaded: " + path_);
  if (tex_ && tex_r_ == &r) return tex_;
  release_texture();
  tex_ = r.create_texture_rgba8(src_w_, src_h_, rgba_.data());
  if (!tex_)
    throw std::runtime_error("create_texture_rgba8 failed: " + path_);
  tex_r_ = &r;
  return tex_;
}
void TextureImage::draw(Renderer& r, Rect dst, Color tint, float radius) {
  void* tex = ensure_texture(r);
  TexturedQuad q;
  q.dst = dst;
  q.uv = Rect{0.f, 0.f, float(src_w_), float(src_h_)};
  r.draw_textured_quads(tex, &q, 1, tint, radius);
}

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


Pressable::Pressable(std::function<void()> on_click, ControlOptions opt)
  : Control(std::move(opt)), on_click_(std::move(on_click)) {}
void Pressable::on_pointer(const PointerEvent& e) {
  if (!opt_.visible || opt_.disabled) return;
  if (e.down && hit_test(e.x, e.y)) {
    pressed_ = true;
    if (page_) page_->update();
    return;
  }
  if (e.up) {
    // Snapshot before on_click_: dialog action may pop_dialog and destroy this.
    const bool fire = pressed_ && hit_test(e.x, e.y);
    pressed_ = false;
    Page* p = page_;
    auto click = on_click_;
    if (p) p->update();
    if (fire && click) click(); // may destroy *this — must be last
  }
}

ButtonBase::ButtonBase(std::string label, std::function<void()> on_click,
                       std::string leading_icon_path, ControlOptions opt)
  : Pressable(std::move(on_click), std::move(opt)),
    label_(std::move(label)) {
  if (label_.size() > kMaxTextBytes) label_.resize(kMaxTextBytes);
  if (!leading_icon_path.empty()) {
    if (leading_icon_path.size() > kMaxPathBytes)
      throw std::invalid_argument("ButtonBase icon path exceeds kMaxPathBytes");
    leading_ = std::make_unique<TextureImage>(std::move(leading_icon_path));
  }
}
ButtonBase::~ButtonBase() = default;
void ButtonBase::set_corner_radius(float radius) {
  corner_radius_ = clamp_radius(radius);
  if (page_) page_->update();
}
float ButtonBase::corner_radius() const { return corner_radius_; }
Size ButtonBase::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width || opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  return measure_button_label(label_, static_cast<bool>(leading_), max_w, max_h);
}
void ButtonBase::paint(Renderer& r) {
  if (!opt_.visible) return;
  paint_background(r);
  paint_centered_label(r, rect_, label_, leading_.get(), content_color());
}
bool ButtonBase::hit_test(float x, float y) const {
  return hit_round_rect(x, y, rect_, corner_radius_);
}

FilledButton::FilledButton(std::string label, std::function<void()> on_click,
                           ControlOptions opt)
  : ButtonBase(std::move(label), std::move(on_click), "", std::move(opt)) {}
void FilledButton::paint_background(Renderer& r) {
  Color bg = pressed() ? colors::kPrimaryContainer : colors::kPrimary;
  r.fill_rect(rect_, bg, corner_radius());
}
Color FilledButton::content_color() const {
  return pressed() ? colors::kOnPrimaryContainer : colors::kOnPrimary;
}

ElevatedButton::ElevatedButton(std::string label, std::function<void()> on_click,
                               std::string icon, ControlOptions opt)
  : ButtonBase(std::move(label), std::move(on_click), std::move(icon), std::move(opt)) {}
void ElevatedButton::paint_background(Renderer& r) {
  Color bg = pressed() ? colors::kSurfaceContainerHigh : colors::kSurfaceContainerLow;
  r.fill_rect(rect_, bg, corner_radius());
}
Color ElevatedButton::content_color() const { return colors::kPrimary; }

OutlinedButton::OutlinedButton(std::string label, std::function<void()> on_click,
                               ControlOptions opt)
  : ButtonBase(std::move(label), std::move(on_click), "", std::move(opt)) {}
void OutlinedButton::paint_background(Renderer& r) {
  if (pressed()) {
    r.fill_rect(rect_, colors::kSurfaceContainer, corner_radius());
  }
  r.stroke_rect(rect_, colors::kOutlineVariant, kStrokeW, corner_radius());
}
Color OutlinedButton::content_color() const { return colors::kOnSurfaceVariant; }

TextButton::TextButton(std::string label, std::function<void()> on_click,
                       ControlOptions opt)
  : ButtonBase(std::move(label), std::move(on_click), "", std::move(opt)) {}
void TextButton::paint_background(Renderer& r) {
  if (pressed()) {
    r.fill_rect(rect_, colors::kSurfaceContainer, corner_radius());
  }
}
Color TextButton::content_color() const { return colors::kPrimary; }

IconButton::IconButton(std::string icon_path, std::function<void()> on_click,
                       ControlOptions opt)
  : Pressable(std::move(on_click), std::move(opt)), image_(std::move(icon_path)) {
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
  if (pressed()) {
    r.fill_rect(rect_, colors::kPrimaryContainer, radius);
  }
  const float side = kIconPx;
  Rect dst{
    rect_.x + (rect_.w - side) * 0.5f,
    rect_.y + (rect_.h - side) * 0.5f,
    side, side};
  Color fg = pressed() ? colors::kOnPrimaryContainer : colors::kOnSurface;
  image_.draw(r, dst, fg);
}
bool IconButton::hit_test(float x, float y) const {
  const float radius = std::min(rect_.w, rect_.h) * 0.5f;
  return hit_round_rect(x, y, rect_, radius);
}

Checkbox::Checkbox(std::string label, bool value,
                   std::function<void(bool)> on_change, ControlOptions opt)
  : Pressable([this]() {
      value_ = !value_;
      if (page_) page_->update();
      if (on_change_) on_change_(value_);
    }, std::move(opt)),
    label_(std::move(label)), value_(value),
    on_change_(std::move(on_change)), check_icon_("icons/check.png") {
  if (label_.size() > kMaxTextBytes) label_.resize(kMaxTextBytes);
}
bool Checkbox::value() const { return value_; }
void Checkbox::set_value(bool v) {
  if (value_ == v) return;
  value_ = v;
  if (page_) page_->update();
  if (on_change_) on_change_(value_);
}
Size Checkbox::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width || opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  float w = kBox;
  float h = kBox;
  if (!label_.empty()) {
    Size t = default_font().measure(label_, kLabelPx);
    w += kLabelGap + t.w;
    if (t.h > h) h = t.h;
  }
  // Match Python toggle row height comfort (~40) when labeled.
  if (!label_.empty() && h < 40.f) h = 40.f;
  Size s{w, h};
  if (max_w && s.w > *max_w) s.w = *max_w;
  if (max_h && s.h > *max_h) s.h = *max_h;
  return s;
}
void Checkbox::paint(Renderer& r) {
  if (!opt_.visible) return;
  const float box_y = rect_.y + (rect_.h - kBox) * 0.5f;
  const Rect box{rect_.x, box_y, kBox, kBox};
  if (value_) {
    r.fill_rect(box, colors::kPrimary, kBoxRadius);
    const float side = kCheckPx;
    Rect idst{
      box.x + (kBox - side) * 0.5f,
      box.y + (kBox - side) * 0.5f,
      side, side};
    check_icon_.draw(r, idst, colors::kOnPrimary);
  } else {
    r.stroke_rect(box, colors::kOnSurfaceVariant, 2.f, kBoxRadius);
  }
  if (!label_.empty()) {
    Size t = default_font().measure(label_, kLabelPx);
    float tx = rect_.x + kBox + kLabelGap;
    float ty = rect_.y + (rect_.h - t.h) * 0.5f;
    default_font().draw(r, tx, ty, label_, colors::kOnSurface, kLabelPx);
  }
}
Slider::Slider(float min_v, float max_v, int divisions,
               std::function<void(float)> on_change, ControlOptions opt)
  : Control(std::move(opt)), min_(min_v), max_(max_v), divisions_(divisions),
    on_change_(std::move(on_change)) {
  if (!(std::isfinite(min_) && std::isfinite(max_)) || max_ < min_)
    throw std::invalid_argument("Slider min/max invalid");
  if (divisions_ < 0 || divisions_ > kMaxSliderDivisions)
    throw std::invalid_argument("Slider divisions out of range");
  value_ = min_;
  if (!opt_.width) opt_.width = kDefaultWidth;
  if (!opt_.height) opt_.height = kDefaultHeight;
}
float Slider::value() const { return value_; }
void Slider::set_value(float v) { apply_value(v); }
float Slider::value_from_x(float x) const {
  const float pad = 2.f;
  const float track_x = rect_.x + pad;
  const float track_w = std::max(1.f, rect_.w - 2.f * pad);
  float k = (x - track_x) / track_w;
  if (k < 0.f) k = 0.f;
  if (k > 1.f) k = 1.f;
  float v = min_ + k * (max_ - min_);
  if (divisions_ > 0 && max_ > min_) {
    const float step = (max_ - min_) / float(divisions_);
    v = min_ + std::round((v - min_) / step) * step;
  }
  if (v < min_) v = min_;
  if (v > max_) v = max_;
  return v;
}
void Slider::apply_value(float v) {
  if (!(std::isfinite(v)))
    throw std::invalid_argument("Slider value must be finite");
  if (v < min_) v = min_;
  if (v > max_) v = max_;
  if (v == value_) return;
  value_ = v;
  if (page_) page_->update();
  if (on_change_) on_change_(value_);
}
Size Slider::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  Size s{opt_.width.value_or(kDefaultWidth), opt_.height.value_or(kDefaultHeight)};
  if (max_w && s.w > *max_w) s.w = *max_w;
  if (max_h && s.h > *max_h) s.h = *max_h;
  return s;
}
void Slider::paint(Renderer& r) {
  if (!opt_.visible) return;
  const float cy = rect_.y + rect_.h * 0.5f;
  const float pad = 2.f;
  const float track_x = rect_.x + pad;
  const float track_w = std::max(1.f, rect_.w - 2.f * pad);
  const float span = (max_ > min_) ? (max_ - min_) : 1.f;
  const float k = (value_ - min_) / span;
  const float thumb_x = track_x + track_w * k;
  const float handle_w = 4.f;
  const float gap = handle_w * 0.5f + 6.f;
  Color active = colors::kPrimary;
  Color inactive = colors::kSecondaryContainer;

  const float active_end = std::max(track_x, thumb_x - gap);
  const float active_w = active_end - track_x;
  if (active_w > 8.f) {
    r.fill_rect(Rect{track_x, cy - 8.f, active_w, 16.f}, active,
                std::min(8.f, active_w * 0.5f));
  }
  const float inactive_x = std::min(track_x + track_w, thumb_x + gap);
  const float inactive_w = track_x + track_w - inactive_x;
  if (inactive_w > 8.f) {
    r.fill_rect(Rect{inactive_x, cy - 8.f, inactive_w, 16.f}, inactive,
                std::min(8.f, inactive_w * 0.5f));
  }
  if (divisions_ > 1) {
    for (int step = 1; step < divisions_; ++step) {
      float tick_x = track_x + track_w * float(step) / float(divisions_);
      if (std::fabs(tick_x - thumb_x) > gap) {
        Color tick = tick_x < thumb_x ? inactive : active;
        r.fill_rect(Rect{tick_x - 2.f, cy - 2.f, 4.f, 4.f}, tick, 2.f);
      }
    }
  }
  r.fill_rect(Rect{thumb_x - handle_w * 0.5f, cy - 22.f, handle_w, 44.f},
              active, handle_w * 0.5f);
}
void Slider::on_pointer(const PointerEvent& e) {
  if (!opt_.visible || opt_.disabled) return;
  if (e.down && hit_test(e.x, e.y)) {
    dragging_ = true;
    apply_value(value_from_x(e.x));
  }
  if (e.move && dragging_) {
    apply_value(value_from_x(e.x));
  }
  if (e.up) {
    if (dragging_) apply_value(value_from_x(e.x));
    dragging_ = false;
  }
}

Image::Image(std::string path, ControlOptions opt, float border_radius)
  : Control(std::move(opt)), image_(std::move(path)) {
  set_border_radius(border_radius);
}
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
void Image::set_border_radius(float radius) {
  if (!std::isfinite(radius))
    throw std::invalid_argument("Image border_radius must be finite");
  border_radius_ = clamp_radius(radius);
  if (page_) page_->update();
}
float Image::border_radius() const { return border_radius_; }
bool Image::loaded() const { return image_.loaded(); }
Size Image::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  if (opt_.width && opt_.height) return Control::intrinsic(opt_.width, opt_.height);
  image_.ensure_loaded();
  const int src_w = image_.src_w();
  const int src_h = image_.src_h();
  const bool ok = image_.loaded();
  float w = opt_.width.value_or(ok ? float(src_w) : 0.f);
  float h = opt_.height.value_or(ok ? float(src_h) : 0.f);
  if (!opt_.width && !opt_.height && ok) {
    w = float(src_w);
    h = float(src_h);
  } else if (opt_.width && !opt_.height && ok && src_w > 0) {
    h = (*opt_.width) * float(src_h) / float(src_w);
  } else if (!opt_.width && opt_.height && ok && src_h > 0) {
    w = (*opt_.height) * float(src_w) / float(src_h);
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
  image_.ensure_loaded();
  if (!image_.loaded()) return;
  const int src_w = image_.src_w();
  const int src_h = image_.src_h();
  // BoxFit.CONTAIN when both axes are constrained by the laid-out rect.
  float scale = 1.f;
  if (src_w > 0 && src_h > 0 && rect_.w > 0.f && rect_.h > 0.f) {
    scale = std::min(rect_.w / float(src_w), rect_.h / float(src_h));
  }
  float dw = float(src_w) * scale;
  float dh = float(src_h) * scale;
  if (dw > float(kMaxLayoutDim)) dw = float(kMaxLayoutDim);
  if (dh > float(kMaxLayoutDim)) dh = float(kMaxLayoutDim);
  Rect dst{
    rect_.x + (rect_.w - dw) * 0.5f,
    rect_.y + (rect_.h - dh) * 0.5f,
    dw, dh};
  Color tint = has_tint_ ? tint_ : Color{255, 255, 255, 255};
  image_.draw(r, dst, tint, border_radius_);
}

Switch::Switch(bool value, std::function<void(bool)> on_change, ControlOptions opt)
  : Pressable([this]() {
      value_ = !value_;
      if (page_) page_->update();
      if (on_change_) on_change_(value_);
    }, std::move(opt)),
    value_(value), on_change_(std::move(on_change)) {
  if (!opt_.width) opt_.width = kTrackW;
  if (!opt_.height) opt_.height = kHeight;
}
bool Switch::value() const { return value_; }
void Switch::set_value(bool v) {
  if (value_ == v) return;
  value_ = v;
  if (page_) page_->update();
  if (on_change_) on_change_(value_);
}
Size Switch::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  Size s{opt_.width.value_or(kTrackW), opt_.height.value_or(kHeight)};
  if (max_w && s.w > *max_w) s.w = *max_w;
  if (max_h && s.h > *max_h) s.h = *max_h;
  return s;
}
void Switch::paint(Renderer& r) {
  if (!opt_.visible) return;
  const float track_w = kTrackW;
  const float track_h = kTrackH;
  const float track_x = rect_.x + (rect_.w - track_w) * 0.5f;
  const float track_y = rect_.y + (rect_.h - track_h) * 0.5f;
  const Rect track{track_x, track_y, track_w, track_h};
  const float radius = track_h * 0.5f;
  if (value_) {
    r.fill_rect(track, colors::kPrimary, radius);
  } else {
    r.fill_rect(track, colors::kSurfaceContainerHighest, radius);
    r.stroke_rect(track, colors::kOutline, 2.f, radius);
  }
  // Thumb: off r=8 centered at x+16; on r=12 centered at x+(w-16).
  const float thumb_r = value_ ? 12.f : 8.f;
  const float tx = value_ ? (track_x + track_w - 16.f) : (track_x + 16.f);
  const float ty = track_y + track_h * 0.5f;
  Color thumb = value_ ? colors::kOnPrimary : colors::kOutline;
  r.fill_rect(Rect{tx - thumb_r, ty - thumb_r, thumb_r * 2.f, thumb_r * 2.f},
              thumb, thumb_r);
}
namespace {
// Pixel debt: no angular SDF / line-strip in Renderer yet — approximate the
// stroked arc with overlapping discs along the centerline (batched). Cap 180.
void paint_ring_arc(Renderer& r, float cx, float cy, float outer_r, float stroke,
                    float start_rad, float sweep_rad, Color c) {
  if (!(stroke > 0.f) || !(outer_r > 0.f) || !(std::fabs(sweep_rad) > 1e-6f))
    return;
  const float centerline = std::max(0.f, outer_r - stroke * 0.5f);
  const float abs_sweep = std::fabs(sweep_rad);
  // ~1.5° per segment; hard cap keeps us under kMaxFillRects.
  int segs = static_cast<int>(abs_sweep / 0.026f);
  if (segs < 8) segs = 8;
  if (segs > 180) segs = 180;
  const float step = sweep_rad / float(segs);
  const float half = stroke * 0.5f;
  std::vector<Rect> discs;
  discs.reserve(static_cast<std::size_t>(segs));
  for (int i = 0; i < segs; ++i) {
    const float a = start_rad + step * (float(i) + 0.5f);
    const float x = cx + std::cos(a) * centerline;
    const float y = cy + std::sin(a) * centerline;
    discs.push_back(Rect{x - half, y - half, stroke, stroke});
  }
  // fill_rects is axis-aligned only; round each disc via fill_rect radius.
  for (const Rect& d : discs) r.fill_rect(d, c, half);
}
} // namespace

ProgressRing::ProgressRing(float value, ControlOptions opt)
  : Control(std::move(opt)) {
  if (!(std::isfinite(value)))
    throw std::invalid_argument("ProgressRing value must be finite");
  if (value < 0.f) value = 0.f;
  if (value > 1.f) value = 1.f;
  value_ = value;
  if (!opt_.width) opt_.width = kSide;
  if (!opt_.height) opt_.height = kSide;
}
float ProgressRing::value() const { return value_; }
void ProgressRing::set_value(float v) {
  if (!(std::isfinite(v)))
    throw std::invalid_argument("ProgressRing value must be finite");
  if (v < 0.f) v = 0.f;
  if (v > 1.f) v = 1.f;
  if (v == value_) return;
  value_ = v;
  if (page_) page_->update();
}
Size ProgressRing::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  Size s{opt_.width.value_or(kSide), opt_.height.value_or(kSide)};
  if (max_w && s.w > *max_w) s.w = *max_w;
  if (max_h && s.h > *max_h) s.h = *max_h;
  return s;
}
void ProgressRing::paint(Renderer& r) {
  if (!opt_.visible) return;
  const float side = std::min(rect_.w, rect_.h);
  if (!(side > 0.f)) return;
  float stroke = kStroke;
  if (stroke > side) stroke = side;
  const float cx = rect_.x + rect_.w * 0.5f;
  const float cy = rect_.y + rect_.h * 0.5f;
  // Full track annulus via SDF stroke_rect (circle).
  const Rect ring{cx - side * 0.5f, cy - side * 0.5f, side, side};
  r.stroke_rect(ring, colors::kSecondaryContainer, stroke, side * 0.5f);
  if (value_ <= 0.f) return;
  constexpr float kPi = 3.14159265358979323846f;
  const float start = -0.5f * kPi;
  const float sweep = 2.f * kPi * value_;
  paint_ring_arc(r, cx, cy, side * 0.5f, stroke, start, sweep, colors::kPrimary);
}


Dropdown::Dropdown(std::string hint, std::vector<DropdownOption> options,
                   std::function<void(const std::string& key)> on_select,
                   ControlOptions opt)
  : Control(std::move(opt)), hint_(std::move(hint)),
    options_(std::move(options)), on_select_(std::move(on_select)) {
  if (hint_.size() > kMaxTextBytes)
    throw std::invalid_argument("Dropdown hint exceeds kMaxTextBytes");
  if (options_.size() > kMaxDropdownOptions)
    throw std::invalid_argument("Dropdown options exceed kMaxDropdownOptions");
  for (auto& o : options_) {
    if (o.key.size() > kMaxTextBytes)
      throw std::invalid_argument("Dropdown option key exceeds kMaxTextBytes");
    if (o.text.size() > kMaxTextBytes)
      throw std::invalid_argument("Dropdown option text exceeds kMaxTextBytes");
    if (o.key.empty())
      throw std::invalid_argument("Dropdown option key must be non-empty");
  }
  if (!opt_.width) opt_.width = kDefaultWidth;
}

bool Dropdown::is_open() const { return open_; }
const std::string& Dropdown::value() const { return value_; }
const std::string& Dropdown::selected_text() const { return selected_text_; }

void Dropdown::set_value(std::string key) {
  if (key.empty()) {
    if (value_.empty()) return;
    value_.clear();
    selected_text_.clear();
    if (page_) page_->update();
    return;
  }
  for (const auto& o : options_) {
    if (o.key == key) {
      if (value_ == key) return;
      value_ = o.key;
      selected_text_ = o.text.empty() ? o.key : o.text;
      if (page_) page_->update();
      return;
    }
  }
  throw std::invalid_argument("Dropdown set_value: unknown key");
}

void Dropdown::set_open(bool open) {
  if (open_ == open) return;
  open_ = open;
  if (page_) page_->update();
}

Rect Dropdown::field_rect() const {
  return Rect{rect_.x, rect_.y, rect_.w, kFieldHeight};
}

Rect Dropdown::menu_rect() const {
  const float h = kItemHeight * float(options_.size());
  return Rect{rect_.x, rect_.y + kFieldHeight, rect_.w, h};
}

int Dropdown::hit_option(float x, float y) const {
  if (!open_ || options_.empty()) return -1;
  const Rect m = menu_rect();
  if (!(x >= m.x && y >= m.y && x < m.x + m.w && y < m.y + m.h)) return -1;
  const int idx = static_cast<int>((y - m.y) / kItemHeight);
  if (idx < 0 || idx >= static_cast<int>(options_.size())) return -1;
  return idx;
}

Size Dropdown::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  float w = opt_.width.value_or(kDefaultWidth);
  float h = kFieldHeight;
  if (open_ && !options_.empty())
    h += kItemHeight * float(options_.size());
  if (opt_.height) h = *opt_.height;
  if (max_w && w > *max_w) w = *max_w;
  if (max_h && h > *max_h) h = *max_h;
  if (w > float(kMaxLayoutDim)) w = float(kMaxLayoutDim);
  if (h > float(kMaxLayoutDim)) h = float(kMaxLayoutDim);
  if (w < 0) w = 0;
  if (h < 0) h = 0;
  return {w, h};
}

void Dropdown::paint(Renderer& r) {
  if (!opt_.visible) return;
  const Rect field = field_rect();
  // Closed field: SURFACE_CONTAINER_HIGHEST fill, OUTLINE_VARIANT stroke (M3-ish).
  Color fill = pressed_ && press_option_ == -2
                   ? colors::kSurfaceContainerHigh
                   : colors::kSurfaceContainerHighest;
  r.fill_rect(field, fill, kRadius);
  r.stroke_rect(field, open_ ? colors::kPrimary : colors::kOutlineVariant,
                open_ ? 2.f : 1.f, kRadius);

  const std::string& shown =
      selected_text_.empty() ? hint_ : selected_text_;
  Color fg = selected_text_.empty() ? colors::kOnSurfaceVariant
                                    : colors::kOnSurface;
  Size t = default_font().measure(shown, kTextPx);
  float tx = field.x + kPadH;
  float ty = field.y + (field.h - t.h) * 0.5f;
  default_font().draw(r, tx, ty, shown, fg, kTextPx);

  // Trailing chevron affordance (text, not Material icon — simple popup).
  const char* chev = open_ ? "^" : "v";
  Size cv = default_font().measure(chev, kTextPx);
  default_font().draw(r, field.x + field.w - kPadH - cv.w,
                      field.y + (field.h - cv.h) * 0.5f, chev,
                      colors::kOnSurfaceVariant, kTextPx);

  if (!open_ || options_.empty()) return;
  const Rect menu = menu_rect();
  r.fill_rect(menu, colors::kSurfaceContainer, kRadius);
  r.stroke_rect(menu, colors::kOutlineVariant, 1.f, kRadius);
  for (std::size_t i = 0; i < options_.size(); ++i) {
    const Rect row{menu.x, menu.y + kItemHeight * float(i), menu.w, kItemHeight};
    if (press_option_ == static_cast<int>(i)) {
      r.fill_rect(row, colors::kSurfaceContainerHigh, 0.f);
    }
    const std::string& label =
        options_[i].text.empty() ? options_[i].key : options_[i].text;
    Size lt = default_font().measure(label, kTextPx);
    Color lfg = (options_[i].key == value_) ? colors::kPrimary
                                            : colors::kOnSurface;
    default_font().draw(r, row.x + kPadH,
                        row.y + (row.h - lt.h) * 0.5f, label, lfg, kTextPx);
  }
}

bool Dropdown::hit_test(float x, float y) const {
  if (!opt_.visible) return false;
  if (hit_round_rect(x, y, field_rect(), kRadius)) return true;
  if (open_ && !options_.empty()) {
    const Rect m = menu_rect();
    return x >= m.x && y >= m.y && x < m.x + m.w && y < m.y + m.h;
  }
  return false;
}

void Dropdown::on_pointer(const PointerEvent& e) {
  if (!opt_.visible || opt_.disabled) return;
  if (e.down) {
    const int opt_i = hit_option(e.x, e.y);
    if (opt_i >= 0) {
      pressed_ = true;
      press_option_ = opt_i;
      if (page_) page_->update();
      return;
    }
    if (hit_round_rect(e.x, e.y, field_rect(), kRadius)) {
      pressed_ = true;
      press_option_ = -2;
      if (page_) page_->update();
    }
    return;
  }
  if (e.up) {
    if (!pressed_) return;
    const int was = press_option_;
    pressed_ = false;
    press_option_ = -1;
    if (was == -2 && hit_round_rect(e.x, e.y, field_rect(), kRadius)) {
      open_ = !open_;
      if (page_) page_->update();
      return;
    }
    if (was >= 0) {
      const int now = hit_option(e.x, e.y);
      if (now == was) {
        const auto& o = options_[static_cast<std::size_t>(was)];
        value_ = o.key;
        selected_text_ = o.text.empty() ? o.key : o.text;
        open_ = false;
        if (page_) page_->update();
        if (on_select_) on_select_(value_);
        return;
      }
    }
    if (page_) page_->update();
  }
}


namespace {
void require_text_bytes(const std::string& s, const char* what) {
  if (s.size() > kMaxTextBytes)
    throw std::invalid_argument(std::string(what) + " exceeds kMaxTextBytes");
}
} // namespace

DialogControl::DialogControl(bool barrier, bool modal)
  : Control({}), barrier_(barrier), modal_(modal) {}
void DialogControl::on_shown() {}
void DialogControl::tick() {}
void DialogControl::dismiss() {
  if (page_) page_->pop_dialog(this);
}

AlertDialog::AlertDialog(std::string title, std::string content,
                         std::vector<std::unique_ptr<Control>> actions,
                         bool modal)
  : DialogControl(/*barrier=*/true, modal),
    title_(std::move(title)), content_(std::move(content)) {
  require_text_bytes(title_, "AlertDialog title");
  require_text_bytes(content_, "AlertDialog content");
  if (actions.size() > kMaxDialogActions)
    throw std::invalid_argument("AlertDialog actions exceed kMaxDialogActions");
  for (auto& a : actions) {
    if (!a) throw std::invalid_argument("AlertDialog action is null");
    add_child(std::move(a));
  }
}

bool AlertDialog::point_in_card(float x, float y) const {
  return x >= card_rect_.x && y >= card_rect_.y &&
         x < card_rect_.x + card_rect_.w && y < card_rect_.y + card_rect_.h;
}

void AlertDialog::layout() {
  const float avail_w = std::max(0.f, rect_.w - 2.f * kInset);
  const float avail_h = std::max(0.f, rect_.h - 2.f * kInset);
  Size title_sz = title_.empty() ? Size{0, 0}
                                 : default_font().measure(title_, kTitlePx);
  Size content_sz = content_.empty() ? Size{0, 0}
                                     : default_font().measure(content_, kContentPx);

  float actions_w = 0.f;
  float actions_h = 0.f;
  for (std::size_t i = 0; i < children_.size(); ++i) {
    Control* c = children_[i].get();
    if (!c || !c->options().visible) continue;
    Size s = c->intrinsic({}, {});
    if (i > 0) actions_w += kActionGap;
    actions_w += s.w;
    if (s.h > actions_h) actions_h = s.h;
  }

  float card_w = kMinCardW;
  if (title_sz.w + 2.f * kPad > card_w) card_w = title_sz.w + 2.f * kPad;
  if (content_sz.w + 2.f * kPad > card_w) card_w = content_sz.w + 2.f * kPad;
  if (actions_w + 2.f * kPad > card_w) card_w = actions_w + 2.f * kPad;
  if (card_w > avail_w) card_w = avail_w;
  if (card_w > float(kMaxLayoutDim)) card_w = float(kMaxLayoutDim);

  float card_h = 0.f;
  if (!title_.empty()) card_h += kPad + title_sz.h;
  if (!content_.empty()) card_h += kPad + content_sz.h;
  if (actions_h > 0.f) card_h += kPad + actions_h;
  card_h += kPad; // bottom pad
  if (card_h > avail_h) card_h = avail_h;
  if (card_h > float(kMaxLayoutDim)) card_h = float(kMaxLayoutDim);

  const float cx = rect_.x + kInset + (avail_w - card_w) * 0.5f;
  const float cy = rect_.y + kInset + (avail_h - card_h) * 0.5f;
  card_rect_ = Rect{cx, cy, card_w, card_h};

  float y = cy + kPad;
  if (!title_.empty()) y += title_sz.h + kPad;
  if (!content_.empty()) y += content_sz.h + kPad;

  // Actions end-aligned along the bottom pad row.
  float ax = cx + card_w - kPad - actions_w;
  float ay = cy + card_h - kPad - actions_h;
  for (std::size_t i = 0; i < children_.size(); ++i) {
    Control* c = children_[i].get();
    if (!c || !c->options().visible) continue;
    Size s = c->intrinsic({}, {});
    c->set_rect(Rect{ax, ay + (actions_h - s.h) * 0.5f, s.w, s.h});
    c->layout();
    ax += s.w + kActionGap;
  }
  (void)y;
}

void AlertDialog::paint(Renderer& r) {
  if (!opt_.visible) return;
  r.fill_rect(rect_, colors::kScrim, 0.f);
  r.fill_rect(card_rect_, colors::kSurfaceContainerHigh, kRadius);
  r.clip_push(card_rect_);

  float y = card_rect_.y + kPad;
  if (!title_.empty()) {
    Size ts = default_font().measure(title_, kTitlePx);
    default_font().draw(r, card_rect_.x + kPad, y, title_, colors::kOnSurface,
                        kTitlePx);
    y += ts.h + kPad;
  }
  if (!content_.empty()) {
    default_font().draw(r, card_rect_.x + kPad, y, content_,
                        colors::kOnSurfaceVariant, kContentPx);
  }
  Control::paint(r); // action buttons
  r.clip_pop();
}

bool AlertDialog::hit_test(float x, float y) const {
  // Barrier fills the page — swallows everything.
  return opt_.visible && x >= rect_.x && y >= rect_.y &&
         x < rect_.x + rect_.w && y < rect_.y + rect_.h;
}

void AlertDialog::on_pointer(const PointerEvent& e) {
  if (!opt_.visible || opt_.disabled) return;
  // Scrim / card chrome click: dismiss unless modal. Action buttons are hit
  // as children via hit_target, so they never reach here.
  if (e.down && !modal() && !point_in_card(e.x, e.y)) {
    dismiss();
  }
}

SnackBar::SnackBar(std::string message, std::string action_label,
                   std::function<void()> on_action, int duration_ms)
  : DialogControl(/*barrier=*/false, /*modal=*/false),
    message_(std::move(message)),
    action_label_(std::move(action_label)),
    on_action_(std::move(on_action)),
    duration_ms_(duration_ms) {
  require_text_bytes(message_, "SnackBar message");
  require_text_bytes(action_label_, "SnackBar action label");
  if (duration_ms_ <= 0 || duration_ms_ > kMaxSnackBarDurationMs)
    throw std::invalid_argument("SnackBar duration_ms out of range");
  if (!action_label_.empty()) {
    // Persist while action present (Python default). Action dismisses.
    SnackBar* self = this;
    add_child(std::make_unique<TextButton>(
        action_label_, [self]() {
          if (self->on_action_) self->on_action_();
          self->dismiss();
        }));
  }
}

void SnackBar::on_shown() {
  has_deadline_ = false;
  // With an action label, persist until action / explicit pop (Python).
  if (!action_label_.empty()) return;
  deadline_ = std::chrono::steady_clock::now() +
              std::chrono::milliseconds(duration_ms_);
  has_deadline_ = true;
}

void SnackBar::tick() {
  if (!has_deadline_) return;
  if (std::chrono::steady_clock::now() >= deadline_) {
    has_deadline_ = false;
    dismiss();
  }
}

void SnackBar::layout() {
  Size msg = default_font().measure(message_, kTextPx);
  float action_w = 0.f;
  float action_h = 0.f;
  Control* action = nullptr;
  if (!children_.empty()) action = children_[0].get();
  if (action && action->options().visible) {
    Size s = action->intrinsic({}, {});
    action_w = s.w;
    action_h = s.h;
  }
  float inner_w = std::max(0.f, rect_.w - 2.f * kMargin);
  float bar_w = inner_w;
  if (bar_w > float(kMaxLayoutDim)) bar_w = float(kMaxLayoutDim);
  float content_h = std::max(msg.h, action_h);
  float bar_h = std::max(kMinH, content_h + 2.f * kPad);
  if (bar_h > float(kMaxLayoutDim)) bar_h = float(kMaxLayoutDim);
  float bx = rect_.x + kMargin + (inner_w - bar_w) * 0.5f;
  float by = rect_.y + rect_.h - kMargin - bar_h;
  bar_rect_ = Rect{bx, by, bar_w, bar_h};

  if (action && action->options().visible) {
    Size s = action->intrinsic({}, {});
    float ax = bx + bar_w - kPad - s.w;
    float ay = by + (bar_h - s.h) * 0.5f;
    action->set_rect(Rect{ax, ay, s.w, s.h});
    action->layout();
  }
}

void SnackBar::paint(Renderer& r) {
  if (!opt_.visible) return;
  r.fill_rect(bar_rect_, colors::kInverseSurface, kRadius);
  Size msg = default_font().measure(message_, kTextPx);
  float tx = bar_rect_.x + kPad;
  float ty = bar_rect_.y + (bar_rect_.h - msg.h) * 0.5f;
  default_font().draw(r, tx, ty, message_, colors::kOnInverseSurface, kTextPx);
  Control::paint(r);
}

bool SnackBar::hit_test(float x, float y) const {
  if (!opt_.visible) return false;
  return x >= bar_rect_.x && y >= bar_rect_.y &&
         x < bar_rect_.x + bar_rect_.w && y < bar_rect_.y + bar_rect_.h;
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
