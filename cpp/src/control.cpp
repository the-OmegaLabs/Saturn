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

// Approximate Python painting.draw_shadow (ambient + key) with a few
// translucent rounded fills per layer — no blur kernel / FBO.
// Match painting._shadow rounding (scale=1 logical):
//   ambient_blur = max(1, round((1 + 0.7e) * scale))
//   key_blur     = max(1, round((0.5 + 0.8e) * scale))
//   key_dy       = round(0.5 * e * scale)
// Python3 round is banker's (half to even): e=1 → blur 2/1, dy=0.
// Not containers._draw_shadow / BoxShadow(blur=3*e).

// Python 3 round(): nearest integer, ties to even.
long py_round(double x) {
  const double floored = std::floor(x);
  const double frac = x - floored;
  if (frac < 0.5) return static_cast<long>(floored);
  if (frac > 0.5) return static_cast<long>(floored) + 1;
  const long n = static_cast<long>(floored);
  return (n % 2 == 0) ? n : n + 1;
}

void draw_elevation_shadow(Renderer& r, const Rect& box, float radius,
                           float elevation) {
  if (!std::isfinite(elevation) || !std::isfinite(radius) ||
      !std::isfinite(box.x) || !std::isfinite(box.y) ||
      !std::isfinite(box.w) || !std::isfinite(box.h)) {
    throw std::invalid_argument("draw_elevation_shadow args must be finite");
  }
  if (elevation <= 0.f) return;
  if (!(box.w > 0.f && box.h > 0.f)) return;

  auto paint_layer = [&](float blur, float dy, std::uint8_t alpha) {
    if (!std::isfinite(blur) || !std::isfinite(dy)) {
      throw std::invalid_argument(
          "draw_elevation_shadow layer args must be finite");
    }
    if (blur < 0.f) blur = 0.f;
    if (blur > kMaxCornerRadius) blur = kMaxCornerRadius;
    if (alpha == 0) return;

    constexpr int kSteps = 4;
    // blur==0: still paint silhouette at dy (key offset with tiny e).
    const int steps = blur > 0.f ? kSteps : 1;
    for (int j = steps; j >= 1; --j) {
      const float grow = blur > 0.f ? blur * float(j) / float(kSteps) : 0.f;
      Rect layer{
        box.x - grow,
        box.y - grow + dy,
        box.w + 2.f * grow,
        box.h + 2.f * grow};
      if (!(layer.w > 0.f && layer.h > 0.f)) continue;
      if (layer.w > float(kMaxLayoutDim) || layer.h > float(kMaxLayoutDim)) {
        throw std::invalid_argument(
            "draw_elevation_shadow layer exceeds kMaxLayoutDim");
      }
      const auto a = static_cast<std::uint8_t>(
          std::lround(float(alpha) / float(j + 1)));
      if (a == 0) continue;
      r.fill_rect(layer, Color{0, 0, 0, a}, clamp_radius(radius + grow));
    }
  };

  // painting._shadow with scale=1 (logical demo / golden shots).
  // py_round = Python3 banker's round (not std::lround).
  constexpr double kScale = 1.0;
  const double e = double(elevation);
  const float ambient_blur = float(std::max(
      1L, py_round((1.0 + e * 0.7) * kScale)));
  const float key_blur = float(std::max(
      1L, py_round((0.5 + e * 0.8) * kScale)));
  const float key_dy = float(py_round(e * 0.5 * kScale));
  paint_layer(ambient_blur, 0.f, /*alpha=*/28);
  paint_layer(key_blur, key_dy, /*alpha=*/40);
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
  if (has_icon) w += kLeadingIconPx + kIconGap - 8;
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
  if (leading) x -= 4;
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
  tex_ = r.create_image_texture_rgba8(src_w_, src_h_, rgba_.data());
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
void Control::set_options(ControlOptions opt) {
  opt_ = std::move(opt);
  if (page_) page_->update();
}
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
  if (!opt_.visible || opt_.disabled) return nullptr;
  for (auto it = children_.rbegin(); it != children_.rend(); ++it) {
    Control* c = it->get();
    if (!c || !c->opt_.visible || c->opt_.disabled) continue;
    if (Control* t = c->hit_target(x, y)) return t;
  }
  if (hit_test(x, y)) return this;
  return nullptr;
}
void Control::on_pointer(const PointerEvent&) {}
void Control::on_focus(bool) {}
void Control::on_key(const KeyEvent&) {}
void Control::on_text(const TextEvent&) {}
void Control::on_composition(const CompositionEvent&) {}
bool Control::on_scroll(const ScrollEvent&) { return false; }
void Control::on_hover(bool) {}
Control* Control::hover_target(float x, float y) {
  if (!opt_.visible || opt_.disabled) return nullptr;
  for (auto it = children_.rbegin(); it != children_.rend(); ++it)
    if (*it)
      if (Control* t = (*it)->hover_target(x, y)) return t;
  return accepts_hover() && hit_test(x, y) ? this : nullptr;
}
void Control::tick(double now) {
  animation_time_ = now;
  for (auto& child : children_) if (child) child->tick(now);
}

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
  s.h = default_font().line_height(size_);
  if (max_w && s.w > *max_w) s.w = *max_w;
  return s;
}
void Text::paint(Renderer& r) {
  if (!opt_.visible) return;
  default_font().draw(r, rect_.x, rect_.y, value_, color_, size_);
}


Pressable::Pressable(std::function<void()> on_click, ControlOptions opt)
  : Control(std::move(opt)), on_click_(std::move(on_click)) {}
void Pressable::tick(double now) {
  Control::tick(now);
  state_layer_.tick(now);
}
SaturnLogo::SaturnLogo(Color color, ControlOptions opt)
    : Control(std::move(opt)), color_(color) {
  if (!opt_.width) opt_.width = 52.f;
  if (!opt_.height) opt_.height = 40.f;
}
Size SaturnLogo::intrinsic(OptionalSize max_w,OptionalSize max_h) const {
  return Control::intrinsic(max_w,max_h);
}
void SaturnLogo::paint(Renderer& r) {
  if (!opt_.visible || rect_.w <= 0 || rect_.h <= 0) return;
  const float scale = std::min(rect_.w/104.f,rect_.h/84.f);
  const float w = 104*scale,h = 84*scale;
  r.draw_saturn_mark({rect_.x+(rect_.w-w)/2,rect_.y+(rect_.h-h)/2,w,h},color_);
}
void Pressable::on_hover(bool on) {
  hovered_ = on;
  state_layer_.set_hover(on, animation_time_);
}
void Pressable::on_focus(bool focused) { focused_ = focused; }
void Pressable::on_key(const KeyEvent& e) {
  if (!opt_.visible || opt_.disabled) return;
  if (e.key == Key::Enter || e.key == Key::Space) {
    auto click = on_click_;
    if (click) click();
  }
}
void Pressable::on_pressed(float x, float y) {
  state_layer_.press(x, y, animation_time_);
}
void Pressable::on_released() { state_layer_.release(animation_time_); }
void Pressable::paint_state_layer(Renderer& r, Rect box, Color color, float radius) {
  if (opt_.disabled || box.w <= 0 || box.h <= 0) return;
  if (focused()) {
    Color focus = color;
    focus.a = std::uint8_t(py_round(255*.12));
    r.fill_rect(box,focus,radius);
  }
  const float hover = float(state_layer_.hover.value(animation_time_));
  const float press = float(state_layer_.press_alpha.value(animation_time_));
  if (hover <= 0 && press <= 0) return;
  const float p = float(state_layer_.ripple.value(animation_time_));
  const float ox = std::clamp(state_layer_.origin_x, box.x, box.x + box.w);
  const float oy = std::clamp(state_layer_.origin_y, box.y, box.y + box.h);
  const float rx = ox + (box.x + box.w/2 - ox)*p;
  const float ry = oy + (box.y + box.h/2 - oy)*p;
  float end = 0;
  for (float x : {box.x, box.x + box.w})
    for (float y : {box.y, box.y + box.h})
      end = std::max(end, std::hypot(rx-x, ry-y));
  end += 10;
  const float start = .1f * std::max(box.w, box.h);
  r.state_layer(box, color, radius, hover, press, rx, ry, start+(end-start)*p);
}
void Pressable::on_pointer(const PointerEvent& e) {
  if (e.cancel) {
    if (pressed_) on_released();
    pressed_ = false;
    return;
  }
  if (!opt_.visible || opt_.disabled) return;
  if (e.down && hit_test(e.x, e.y)) {
    pressed_ = true;
    on_pressed(e.x, e.y);
    return;
  }
  if (e.up) {
    // Snapshot before on_click_: dialog action may pop_dialog and destroy this.
    const bool fire = pressed_ && hit_test(e.x, e.y);
    if (pressed_) on_released();
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
  paint_state_layer(r, rect_, content_color(), corner_radius_);
  paint_centered_label(r, rect_, label_, leading_.get(), content_color());
}
bool ButtonBase::hit_test(float x, float y) const {
  return hit_round_rect(x, y, rect_, corner_radius_);
}

FilledButton::FilledButton(std::string label, std::function<void()> on_click,
                           ControlOptions opt)
  : ButtonBase(std::move(label), std::move(on_click), "", std::move(opt)) {}
void FilledButton::paint_background(Renderer& r) {
  r.fill_rect(rect_, colors::kPrimary, corner_radius());
}
Color FilledButton::content_color() const {
  return colors::kOnPrimary;
}

ElevatedButton::ElevatedButton(std::string label, std::function<void()> on_click,
                               std::string icon, ControlOptions opt)
  : ButtonBase(std::move(label), std::move(on_click), std::move(icon), std::move(opt)) {}
void ElevatedButton::paint_background(Renderer& r) {
  if (!opt_.disabled) {
    draw_elevation_shadow(r, rect_, corner_radius(),
                          float(elevation_.value(animation_time_)));
  }
  r.fill_rect(rect_, colors::kSurfaceContainerLow, corner_radius());
}
void ElevatedButton::on_hover(bool on) {
  Pressable::on_hover(on);
  elevation_.animate(on ? 3 : 1, 150, motion::Curve::Emphasized, animation_time_);
}
void ElevatedButton::on_pressed(float x, float y) {
  Pressable::on_pressed(x, y);
  elevation_.animate(1, 150, motion::Curve::Emphasized, animation_time_);
}
void ElevatedButton::on_released() {
  Pressable::on_released();
  elevation_.animate(hovered() ? 3 : 1, 150, motion::Curve::Emphasized, animation_time_);
}
Color ElevatedButton::content_color() const { return colors::kPrimary; }

OutlinedButton::OutlinedButton(std::string label, std::function<void()> on_click,
                               ControlOptions opt)
  : ButtonBase(std::move(label), std::move(on_click), "", std::move(opt)) {}
void OutlinedButton::paint_background(Renderer& r) {
  r.stroke_rect(rect_, colors::kOutlineVariant, kStrokeW, corner_radius());
}
Color OutlinedButton::content_color() const { return colors::kOnSurfaceVariant; }

TextButton::TextButton(std::string label, std::function<void()> on_click,
                       ControlOptions opt)
  : ButtonBase(std::move(label), std::move(on_click), "", std::move(opt)) {}
void TextButton::paint_background(Renderer& r) {
  (void)r;
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
  paint_state_layer(r, rect_, colors::kOnSurfaceVariant, radius);
  const float side = kIconPx;
  Rect dst{
    rect_.x + (rect_.w - side) * 0.5f,
    rect_.y + (rect_.h - side) * 0.5f,
    side, side};
  Color fg = colors::kOnSurfaceVariant;
  image_.draw(r, dst, fg);
}
bool IconButton::hit_test(float x, float y) const {
  const float radius = std::min(rect_.w, rect_.h) * 0.5f;
  return hit_round_rect(x, y, rect_, radius);
}

Checkbox::Checkbox(std::string label, bool value,
                   std::function<void(bool)> on_change, ControlOptions opt)
  : Pressable([this]() {
      set_value(!value_);
      if (on_change_) on_change_(value_);
    }, std::move(opt)),
    label_(std::move(label)), value_(value),
    value_progress_(value ? 1 : 0), on_change_(std::move(on_change)),
    check_icon_("icons/check.png") {
  if (label_.size() > kMaxTextBytes) label_.resize(kMaxTextBytes);
  state_layer_.ripple_ms = 450;
  state_layer_.press_ms = 105;
  state_layer_.minimum_ms = 225;
  state_layer_.fade_ms = 375;
}
bool Checkbox::value() const { return value_; }
void Checkbox::set_value(bool v) {
  if (value_ == v) return;
  value_ = v;
  value_progress_.animate(v ? 1 : 0, v ? 350 : 150,
      v ? motion::Curve::EmphasizedDecelerate : motion::Curve::EmphasizedAccelerate,
      animation_time_);
  if (page_) page_->update();
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
  Size s{w, h};
  if (max_w && s.w > *max_w) s.w = *max_w;
  if (max_h && s.h > *max_h) s.h = *max_h;
  return s;
}
void Checkbox::paint(Renderer& r) {
  if (!opt_.visible) return;
  const float box_y = rect_.y + (rect_.h - kBox) * 0.5f;
  const Rect box{rect_.x, box_y, kBox, kBox};
  paint_state_layer(r, {box.x+kBox/2-20, box.y+kBox/2-20, 40, 40},
                    value_ ? colors::kPrimary : colors::kOnSurface, 20);
  const float progress = float(value_progress_.value(animation_time_));
  if (progress > 0) {
    const float scale = .6f + .4f*progress;
    const float selected_size = kBox*scale;
    Color fill = colors::kPrimary;
    fill.a = std::uint8_t(std::lround(255 * std::min(1.f, progress*3)));
    r.fill_rect({box.x+(kBox-selected_size)/2, box.y+(kBox-selected_size)/2,
                 selected_size, selected_size}, fill, kBoxRadius);
    const float side = kCheckPx*scale;
    Rect idst{
      box.x + (kBox - side) * 0.5f,
      box.y + (kBox - side) * 0.5f,
      side, side};
    Color icon = colors::kOnPrimary;
    icon.a = fill.a;
    check_icon_.draw(r, idst, icon);
  }
  if (progress < 1) {
    Color outline = colors::kOnSurfaceVariant;
    outline.a = std::uint8_t(std::lround(255*(1-progress)));
    r.stroke_rect(box, outline, 2.f, kBoxRadius);
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
  : Pressable({},std::move(opt)), min_(min_v), max_(max_v), divisions_(divisions),
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
    v = min_ + float(py_round((v - min_) / step)) * step;
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
  const float handle_w = std::clamp(4-2*float(thumb_press_.value(animation_time_)),2.f,4.f);
  const float gap = handle_w * 0.5f + 6.f;
  Color active = colors::kPrimary;
  Color inactive = colors::kSecondaryContainer;

  const float active_end = std::max(track_x, thumb_x - gap);
  const float active_w = active_end - track_x;
  if (active_w > 8.f) {
    r.fill_rect(Rect{track_x, cy - 8.f, active_w, 16.f}, active,
                std::min(8.f, active_w * 0.5f));
    if (active_w >= 20)
      r.fill_rect({active_end-10,cy-8,10,16},active,2);
  }
  const float inactive_x = std::min(track_x + track_w, thumb_x + gap);
  const float inactive_w = track_x + track_w - inactive_x;
  if (inactive_w > 8.f) {
    r.fill_rect(Rect{inactive_x, cy - 8.f, inactive_w, 16.f}, inactive,
                std::min(8.f, inactive_w * 0.5f));
    if (inactive_w >= 20)
      r.fill_rect({inactive_x,cy-8,10,16},inactive,2);
    r.fill_rect({track_x+track_w-10,cy-2,4,4},active,2);
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
  paint_state_layer(r,{thumb_x-20,cy-20,40,40},active,20);
  r.fill_rect(Rect{thumb_x - handle_w * 0.5f, cy - 22.f, handle_w, 44.f},
              active, handle_w * 0.5f);
}
void Slider::on_pointer(const PointerEvent& e) {
  if (e.cancel) {
    if (dragging_) on_released();
    dragging_ = false;
    return;
  }
  if (!opt_.visible || opt_.disabled) return;
  if (e.down && hit_test(e.x, e.y)) {
    dragging_ = true;
    on_pressed(e.x,e.y);
    apply_value(value_from_x(e.x));
  }
  if (e.move && dragging_) {
    apply_value(value_from_x(e.x));
  }
  if (e.up) {
    if (dragging_) apply_value(value_from_x(e.x));
    if (dragging_) on_released();
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
  if (fit_ == Fit::Fill) { dw = rect_.w; dh = rect_.h; }
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
      set_value(!value_);
      if (on_change_) on_change_(value_);
    }, std::move(opt)),
    value_(value), on_change_(std::move(on_change)),
    position_(value ? 1 : 0), color_(value ? 1 : 0), size_(value ? 1 : 0) {
  if (!opt_.width) opt_.width = kTrackW;
  if (!opt_.height) opt_.height = kHeight;
}
bool Switch::value() const { return value_; }
void Switch::set_value(bool v) {
  if (value_ == v) return;
  value_ = v;
  animate_value();
  if (page_) page_->update();
}
void Slider::on_pressed(float x,float y) {
  state_layer_.ripple_ms = 450; state_layer_.press_ms = 105;
  state_layer_.minimum_ms = 225; state_layer_.fade_ms = 375;
  Pressable::on_pressed(x,y);
  thumb_press_.animate(1,100,motion::Curve::EmphasizedDecelerate,animation_time_);
}
void Slider::on_released() {
  Pressable::on_released();
  thumb_press_.animate(0,100,motion::Curve::EmphasizedAccelerate,animation_time_);
}
void Slider::on_key(const KeyEvent& e) {
  if (opt_.disabled || !opt_.visible) return;
  const float step = (max_-min_)/(divisions_ ? divisions_ : 20);
  if (e.key == Key::Home) apply_value(min_);
  else if (e.key == Key::End) apply_value(max_);
  else if (e.key == Key::Left || e.key == Key::Down) apply_value(value_-step);
  else if (e.key == Key::Right || e.key == Key::Up) apply_value(value_+step);
}
void Switch::animate_value() {
  const double target = value_ ? 1 : 0;
  position_.animate(target, 300, motion::Curve::SwitchOvershoot, animation_time_);
  color_.animate(target, 67, motion::Curve::Linear, animation_time_);
  size_.animate(target, 250, motion::Curve::Standard, animation_time_);
}
void Switch::on_pressed(float x, float y) {
  Pressable::on_pressed(x, y);
  thumb_press_.animate(1, 75, motion::Curve::StandardAccelerate, animation_time_);
  drag_start_x_ = x;
  drag_start_progress_ = position_.value(animation_time_);
  dragged_ = false;
}
void Switch::on_released() {
  Pressable::on_released();
  thumb_press_.animate(0, 100, motion::Curve::StandardDecelerate, animation_time_);
}
void Switch::on_pointer(const PointerEvent& e) {
  if (e.cancel) {
    if (dragged_) animate_value();
    dragged_ = false;
    Pressable::on_pointer(e);
    return;
  }
  if (!opt_.visible || opt_.disabled) return;
  if (e.move && pressed()) {
    const float delta = e.x - drag_start_x_;
    if (std::abs(delta) < 2 && !dragged_) return;
    dragged_ = true;
    const double p = std::clamp(drag_start_progress_ + delta / 20, 0.0, 1.0);
    position_.reset(p); color_.reset(p); size_.reset(p);
    return;
  }
  if (e.up && pressed() && dragged_) {
    const bool selected = position_.value(animation_time_) >= .5;
    const bool changed = selected != value_;
    value_ = selected;
    animate_value();
    on_released();
    set_pressed(false);
    dragged_ = false;
    if (changed && on_change_) on_change_(value_);
    return;
  }
  Pressable::on_pointer(e);
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
  const float p = float(position_.value(animation_time_));
  const float cp = float(color_.value(animation_time_));
  const float sp = float(size_.value(animation_time_));
  auto mix = [cp](Color a, Color b) {
    auto channel = [cp](int a, int b) { return std::uint8_t(py_round(a+(b-a)*cp)); };
    return Color{channel(a.r,b.r), channel(a.g,b.g), channel(a.b,b.b), channel(a.a,b.a)};
  };
  float thumb_r = 8+4*sp;
  thumb_r += (14-thumb_r)*float(thumb_press_.value(animation_time_));
  const float tx = track_x + 16 + 20*p;
  const float ty = track_y + track_h * 0.5f;
  paint_state_layer(r, {tx-20, ty-20, 40, 40},
                    value_ ? colors::kPrimary : colors::kOnSurface, 20);
  r.fill_rect(track, mix(colors::kSurfaceContainerHighest, colors::kPrimary), radius);
  if (cp < 1) {
    Color outline = colors::kOutline;
    outline.a = std::uint8_t(py_round(255*(1-cp)));
    r.stroke_rect(track, outline, 2, radius);
  }
  Color thumb = mix(colors::kOutline, colors::kOnPrimary);
  r.fill_rect(Rect{tx - thumb_r, ty - thumb_r, thumb_r * 2.f, thumb_r * 2.f},
              thumb, thumb_r);
}
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
  if (!(stroke > 0.f)) return;
  const float cx = rect_.x + rect_.w * 0.5f;
  const float cy = rect_.y + rect_.h * 0.5f;
  const float outer = side * 0.5f;
  // Match Python ProgressRing: start=-π/2, round-capped stroke_arc, track gap.
  constexpr float kPi = 3.14159265358979323846f;
  constexpr float kTau = 2.f * kPi;
  constexpr float kTrackGap = 4.f; // Python default (non-year_2023)
  const float start = -0.5f * kPi;
  const float sweep = kTau * value_;
  if (value_ <= 0.f) {
    // Full track when idle.
    r.stroke_arc(cx, cy, outer, start, kTau, colors::kSecondaryContainer, stroke);
    return;
  }
  // Track is the complementary arc with Material track_gap (not a full ring).
  const float gap = (std::min)(sweep, 2.f * (kTrackGap + stroke) / side);
  const float track_sweep = kTau - sweep - 2.f * gap;
  if (track_sweep > 1e-6f)
    r.stroke_arc(cx, cy, outer, start + sweep + gap, track_sweep,
                 colors::kSecondaryContainer, stroke);
  r.stroke_arc(cx, cy, outer, start, sweep, colors::kPrimary, stroke);
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
  if (open_ == open && !(open && menu_closing_)) return;
  open_ = open;
  if (open) {
    menu_closing_ = false;
    menu_close_at_ = -1;
    if (page_) page_->set_active_menu(this);
    menu_progress_.animate(1,300,motion::Curve::Emphasized,animation_time_);
    menu_timeline_.animate(1,300,motion::Curve::Linear,animation_time_);
  } else {
    menu_closing_ = true;
    menu_close_at_ = animation_time_+.15;
    menu_progress_.animate(.35,150,motion::Curve::EmphasizedAccelerate,animation_time_);
    menu_timeline_.animate(0,150,motion::Curve::Linear,animation_time_);
  }
  if (page_) page_->update();
}
void Dropdown::tick(double now) {
  Control::tick(now);
  if (menu_closing_ && now >= menu_close_at_) {
    menu_closing_ = false;
    menu_progress_.reset(0); menu_timeline_.reset(0);
    if (page_) page_->clear_active_menu(this);
  }
}
void Dropdown::on_hover(bool on) {
  hover_progress_.animate(on ? 1 : 0,150,motion::Curve::Standard,animation_time_);
}
void Dropdown::on_focus(bool on) {
  focus_progress_.animate(on ? 1 : 0,150,motion::Curve::Standard,animation_time_);
}
void Dropdown::pick_option(int index) {
  if (index < 0 || index >= int(options_.size())) return;
  const auto& o = options_[std::size_t(index)];
  value_ = o.key;
  selected_text_ = o.text.empty() ? o.key : o.text;
  set_open(false);
  if (on_select_) on_select_(value_);
}
void Dropdown::on_key(const KeyEvent& e) {
  if (e.key == Key::Escape) set_open(false);
  else if (e.key == Key::Enter || e.key == Key::Space) {
    if (open_) pick_option(keyboard_index_);
    else set_open(true);
  } else if (e.key == Key::Down || e.key == Key::Up) {
    if (!open_) set_open(true);
    else if (!options_.empty()) keyboard_index_ = std::clamp(
        keyboard_index_+(e.key == Key::Down ? 1 : -1),0,int(options_.size())-1);
  }
}
bool Dropdown::on_scroll(const ScrollEvent& e) {
  if (!open_ || !menu_hit_test(e.x,e.y) || !std::isfinite(e.delta_y)) return false;
  menu_offset_ = std::clamp(menu_offset_-e.delta_y*40,0.f,
      std::max(0.f,kItemHeight*float(options_.size())-menu_rect().h));
  return true;
}

Rect Dropdown::field_rect() const {
  return Rect{rect_.x, rect_.y, rect_.w, kFieldHeight};
}

Rect Dropdown::menu_rect() const {
  const Rect page = page_ ? page_->rect() : Rect{0,0,float(kMaxLayoutDim),float(kMaxLayoutDim)};
  const float w = std::min(rect_.w,page.w);
  const float h = std::min({kItemHeight*float(options_.size()),320.f,std::max(0.f,page.h-8)});
  const float x = std::clamp(rect_.x,page.x,std::max(page.x,page.x+page.w-w));
  float y = rect_.y+kFieldHeight+4;
  if (y+h > page.y+page.h) y = std::max(page.y,rect_.y-h-4);
  return {x,y,w,h};
}
bool Dropdown::menu_hit_test(float x,float y) const {
  if (!open_ || menu_closing_) return false;
  const Rect m = menu_rect();
  const float h = m.h*float(menu_progress_.value(animation_time_));
  return x >= m.x && x < m.x+m.w && y >= m.y && y < m.y+h;
}

int Dropdown::hit_option(float x, float y) const {
  if (!open_ || options_.empty()) return -1;
  const Rect m = menu_rect();
  if (!menu_hit_test(x,y)) return -1;
  const int idx = static_cast<int>((y - m.y+menu_offset_) / kItemHeight);
  if (idx < 0 || idx >= static_cast<int>(options_.size())) return -1;
  return idx;
}

Size Dropdown::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  float w = opt_.width.value_or(kDefaultWidth);
  float h = kFieldHeight;
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
  const float focus = float(focus_progress_.value(animation_time_));
  const float hover = float(hover_progress_.value(animation_time_));
  auto mix = [](Color a, Color b, float p) {
    auto c = [p](int a,int b) { return std::uint8_t(py_round(a+(b-a)*p)); };
    return Color{c(a.r,b.r),c(a.g,b.g),c(a.b,b.b),c(a.a,b.a)};
  };
  r.stroke_rect(field,mix(mix(colors::kOutline,colors::kOnSurface,.25f*hover),
                         colors::kPrimary,focus),1+focus,kRadius);

  const std::string& shown =
      selected_text_.empty() ? hint_ : selected_text_;
  Color fg = selected_text_.empty() ? colors::kOnSurfaceVariant
                                    : colors::kOnSurface;
  Size t = default_font().measure(shown, kTextPx);
  float tx = field.x + kPadH;
  float ty = field.y + (field.h - t.h) * 0.5f;
  default_font().draw(r, tx, ty, shown, fg, kTextPx);

  // Chevron built from capped solid segments, independent of font glyph metrics.
  const float cx = field.x+field.w-28, cy = field.y+field.h/2;
  for (int i = 0; i < 6; ++i) {
    const float dy = open_ ? -float(i)*.8f+2 : float(i)*.8f-2;
    r.fill_rect({cx-5+float(i),cy+dy,2,2},colors::kOnSurfaceVariant,1);
    r.fill_rect({cx+4-float(i),cy+dy,2,2},colors::kOnSurfaceVariant,1);
  }
}
void Dropdown::paint_menu(Renderer& r) {
  if ((!open_ && !menu_closing_) || options_.empty() || !opt_.visible || opt_.disabled) return;
  Rect menu = menu_rect();
  const float progress = float(menu_progress_.value(animation_time_));
  const float timeline = float(menu_timeline_.value(animation_time_));
  Rect visible = menu;
  visible.h *= progress;
  r.effect_push(0,0,std::min(1.f,timeline*(menu_closing_ ? 3 : 10)));
  draw_elevation_shadow(r,visible,kRadius,8);
  r.fill_rect(visible,colors::kSurfaceContainer,kRadius);
  r.effect_pop();
  r.clip_push(visible);
  for (std::size_t i = 0; i < options_.size(); ++i) {
    const Rect row{menu.x, menu.y + kItemHeight * float(i)-menu_offset_, menu.w, kItemHeight};
    if (row.y+row.h < visible.y || row.y > visible.y+visible.h) continue;
    const float count = float(options_.size());
    float alpha;
    if (menu_closing_) {
      const float delay = 50+50*(count-1-float(i))/count;
      alpha = 1-std::clamp(((1-timeline)*150-delay)/50,0.f,1.f);
    } else alpha = std::clamp((timeline-.5f*float(i)/count)/.5f,0.f,1.f);
    r.effect_push(0,0,alpha);
    if (press_option_ == int(i))
      r.fill_rect(row,colors::kSurfaceContainerHigh,0);
    const std::string& label =
        options_[i].text.empty() ? options_[i].key : options_[i].text;
    Size lt = default_font().measure(label, kTextPx);
    Color lfg = (options_[i].key == value_) ? colors::kPrimary
                                            : colors::kOnSurface;
    default_font().draw(r, row.x + kPadH,
                        row.y + (row.h - lt.h) * 0.5f, label, lfg, kTextPx);
    r.effect_pop();
  }
  r.clip_pop();
}

bool Dropdown::hit_test(float x, float y) const {
  if (!opt_.visible) return false;
  if (hit_round_rect(x, y, field_rect(), kRadius)) return true;
  return false;
}

void Dropdown::on_pointer(const PointerEvent& e) {
  if (e.cancel) { pressed_ = false; press_option_ = -1; return; }
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
      set_open(!open_);
      return;
    }
    if (was >= 0) {
      const int now = hit_option(e.x, e.y);
      if (now == was) {
        pick_option(was);
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
void DialogControl::begin_dismiss() {
  closing_ = true;
  close_at_ = animation_time_;
}
Control* DialogControl::hit_target(float x,float y) {
  if (closing_) return barrier() && hit_test(x,y) ? this : nullptr;
  return Control::hit_target(x,y);
}
void DialogControl::tick(double now) { Control::tick(now); }
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
void AlertDialog::on_shown() {
  closing_ = false;
  reveal_.reset(0); timeline_.reset(0);
  reveal_.animate(1,300,motion::Curve::Emphasized,animation_time_);
  timeline_.animate(1,300,motion::Curve::Linear,animation_time_);
}
void AlertDialog::begin_dismiss() {
  if (closing_) return;
  closing_ = true;
  close_at_ = animation_time_+.15;
  reveal_.animate(.35,150,motion::Curve::EmphasizedAccelerate,animation_time_);
  timeline_.animate(0,150,motion::Curve::Linear,animation_time_);
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
  if (!title_.empty()) title_sz.h = default_font().line_height(kTitlePx);
  if (!content_.empty()) content_sz.h = default_font().line_height(kContentPx);

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
  if (!title_.empty()) card_h += 2*kPad + title_sz.h;
  if (!content_.empty()) card_h += 2*kPad + content_sz.h;
  if (actions_h > 0.f) card_h += 2*kPad + actions_h;
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
  const float reveal = float(reveal_.value(animation_time_));
  const float timeline = float(timeline_.value(animation_time_));
  Color scrim = colors::kScrim;
  scrim.a = std::uint8_t(py_round(scrim.a*timeline));
  r.fill_rect(rect_,scrim);
  Rect visible = card_rect_;
  visible.h *= .35f+.65f*reveal;
  const float dy = -50*(1-reveal);
  const float card_alpha = std::min(1.f,timeline*(closing_ ? 3 : 10));
  const float content_alpha = closing_ ?
      std::clamp((timeline-1.f/3)/(2.f/3),0.f,1.f) :
      std::clamp((timeline-.1f)/.4f,0.f,1.f);
  const float action_alpha = closing_ ? content_alpha :
      std::clamp((timeline-.3f)/.3f,0.f,1.f);
  r.effect_push(0,dy,1);
  r.effect_push(0,0,card_alpha);
  draw_elevation_shadow(r,visible,kRadius,6);
  r.fill_rect(visible,colors::kSurfaceContainerHigh,kRadius);
  r.effect_pop();
  r.clip_push(visible);
  r.effect_push(0,0,content_alpha);

  float y = card_rect_.y + kPad;
  if (!title_.empty()) {
    Size ts = default_font().measure(title_, kTitlePx);
    default_font().draw(r, card_rect_.x + kPad, y, title_, colors::kOnSurface,
                        kTitlePx);
    y += default_font().line_height(kTitlePx) + 2*kPad;
  }
  if (!content_.empty()) {
    default_font().draw(r, card_rect_.x + kPad, y, content_,
                        colors::kOnSurfaceVariant, kContentPx);
  }
  r.effect_pop();
  r.effect_push(0,0,action_alpha);
  Control::paint(r);
  r.effect_pop();
  r.clip_pop();
  r.effect_pop();
}

bool AlertDialog::hit_test(float x, float y) const {
  // Barrier fills the page — swallows everything.
  return opt_.visible && x >= rect_.x && y >= rect_.y &&
         x < rect_.x + rect_.w && y < rect_.y + rect_.h;
}

void AlertDialog::on_pointer(const PointerEvent& e) {
  if (!opt_.visible || opt_.disabled || closing_) return;
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
  closing_ = false;
  reveal_.reset(0);
  reveal_.animate(1,250,motion::Curve::Standard,animation_time_);
  has_deadline_ = false;
  // With an action label, persist until action / explicit pop (Python).
  if (!action_label_.empty()) return;
  deadline_ = animation_time_+duration_ms_/1000.0;
  has_deadline_ = true;
}
void SnackBar::begin_dismiss() {
  if (closing_) return;
  closing_ = true;
  close_at_ = animation_time_+.2;
  reveal_.animate(0,200,motion::Curve::StandardAccelerate,animation_time_);
}

void SnackBar::tick(double now) {
  DialogControl::tick(now);
  if (!has_deadline_) return;
  if (now >= deadline_) {
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
  float bar_h = std::max(kMinH, msg.h+2*kPad);
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
  const float reveal = float(reveal_.value(animation_time_));
  r.effect_push(0,(1-reveal)*48,std::min(1.f,reveal*4));
  draw_elevation_shadow(r,bar_rect_,0,6);
  r.fill_rect(bar_rect_, colors::kInverseSurface, 0);
  Size msg = default_font().measure(message_, kTextPx);
  float tx = bar_rect_.x + kPad;
  float ty = bar_rect_.y + (bar_rect_.h - msg.h) * 0.5f;
  default_font().draw(r, tx, ty, message_, colors::kOnInverseSurface, kTextPx);
  Control::paint(r);
  r.effect_pop();
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
