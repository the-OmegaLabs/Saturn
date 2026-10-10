#include "saturn/control.hpp"
#include "saturn/colors.hpp"
#include "saturn/font.hpp"
#include "saturn/limits.hpp"
#include "saturn/page.hpp"
#include "saturn/renderer.hpp"
#include <SDL3/SDL.h>
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <cctype>

namespace saturn {
namespace {
std::size_t previous(const std::string& s, std::size_t i) {
  if (i == 0) return 0;
  --i;
  while (i > 0 && (static_cast<unsigned char>(s[i]) & 0xc0) == 0x80) --i;
  return i;
}
std::size_t next(const std::string& s, std::size_t i) {
  if (i >= s.size()) return s.size();
  ++i;
  while (i < s.size() && (static_cast<unsigned char>(s[i]) & 0xc0) == 0x80) ++i;
  return i;
}
std::size_t character_index(const std::string& s,int count) {
  std::size_t i = 0;
  for (int n = 0; n < std::max(0,count) && i < s.size(); ++n) i = next(s,i);
  return i;
}
int character_class(const std::string& s,std::size_t i) {
  const auto c = static_cast<unsigned char>(s[i]);
  if (std::isspace(c)) return 0;
  return c >= 128 || std::isalnum(c) || c == '_' ? 1 : 2;
}
std::size_t previous_word(const std::string& s,std::size_t i) {
  while (i > 0 && character_class(s,previous(s,i)) == 0) i = previous(s,i);
  if (!i) return i;
  const int kind = character_class(s,previous(s,i));
  while (i > 0 && character_class(s,previous(s,i)) == kind) i = previous(s,i);
  return i;
}
std::size_t next_word(const std::string& s,std::size_t i) {
  while (i < s.size() && character_class(s,i) == 0) i = next(s,i);
  if (i == s.size()) return i;
  const int kind = character_class(s,i);
  while (i < s.size() && character_class(s,i) == kind) i = next(s,i);
  return i;
}
std::string single_line(std::string text) {
  std::erase(text,'\n');
  std::erase(text,'\r');
  return text;
}
void validate_text(const std::string& s) {
  if (s.size() > kMaxTextLen) throw std::invalid_argument("TextField exceeds kMaxTextLen");
  for (std::size_t i = 0; i < s.size();) {
    unsigned char b = s[i];
    if (b < 32 || b == 127) throw std::invalid_argument("TextField requires single-line text");
    if (b < 128) { ++i; continue; }
    const int count = b >= 0xc2 && b <= 0xdf ? 2 :
                      b >= 0xe0 && b <= 0xef ? 3 :
                      b >= 0xf0 && b <= 0xf4 ? 4 : 0;
    if (count == 0 || i+count > s.size()) throw std::invalid_argument("invalid UTF-8 text");
    for (int j = 1; j < count; ++j)
      if ((static_cast<unsigned char>(s[i+j]) & 0xc0) != 0x80)
        throw std::invalid_argument("invalid UTF-8 continuation");
    const auto second = static_cast<unsigned char>(s[i+1]);
    if ((b == 0xe0 && second < 0xa0) || (b == 0xed && second >= 0xa0) ||
        (b == 0xf0 && second < 0x90) || (b == 0xf4 && second >= 0x90))
      throw std::invalid_argument("invalid UTF-8 scalar");
    i += count;
  }
}
Color mix(Color a, Color b, float p) {
  p = std::clamp(p, 0.f, 1.f);
  auto channel = [p](int a, int b) { return std::uint8_t(std::lround(a+(b-a)*p)); };
  return {channel(a.r,b.r), channel(a.g,b.g), channel(a.b,b.b), channel(a.a,b.a)};
}
}

TextField::TextField(std::string label, std::function<void(const std::string&)> change,
                     std::function<void(const std::string&)> submit, ControlOptions opt)
    : Control(std::move(opt)), label_(std::move(label)),
      on_change_(std::move(change)), on_submit_(std::move(submit)) {
  validate_text(label_);
  clipboard_read_ = [] {
    char* text = SDL_GetClipboardText(); // SDL allocates; freed before returning.
    if (!text) return std::string{};
    std::size_t len = 0;
    while (len <= kMaxTextLen && text[len]) ++len;
    const std::string result = len <= kMaxTextLen ? std::string(text,len) : std::string{};
    SDL_free(text);
    return result;
  };
  clipboard_write_ = [](std::string_view text) {
    if (text.size() > kMaxTextLen) return false;
    return SDL_SetClipboardText(std::string(text).c_str());
  };
}
void TextField::set_clipboard_handlers(std::function<std::string()> read,
                                      std::function<bool(std::string_view)> write) {
  if (!read || !write) throw std::invalid_argument("clipboard handlers cannot be empty");
  clipboard_read_ = std::move(read); clipboard_write_ = std::move(write);
}
void TextField::set_value(std::string value) {
  validate_text(value);
  value_ = std::move(value);
  composition_.clear();
  caret_ = anchor_ = value_.size();
  label_progress_.animate(focused_ || !value_.empty() ? 1 : 0, 150,
                          motion::Curve::Standard, animation_time_);
  reveal_caret();
}
Size TextField::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  Size s{opt_.width.value_or(300), opt_.height.value_or(56)};
  if (max_w) s.w = std::min(s.w, *max_w);
  if (max_h) s.h = std::min(s.h, *max_h);
  return s;
}
void TextField::on_hover(bool on) {
  hover_.animate(on ? 1 : 0, 150, motion::Curve::Standard, animation_time_);
}
void TextField::on_focus(bool on) {
  focused_ = on;
  selecting_ = false;
  if (!on) composition_.clear();
  blink_started_ = animation_time_;
  focus_.animate(on ? 1 : 0, 150, motion::Curve::Standard, animation_time_);
  label_progress_.animate(on || !value_.empty() ? 1 : 0, 150,
                          motion::Curve::Standard, animation_time_);
}
float TextField::caret_x(std::size_t position) const {
  return default_font().measure(std::string_view(value_).substr(0, position), 16).w;
}
void TextField::reveal_caret() {
  const float width = std::max(0.f, rect_.w-32);
  const float x = caret_x(caret_);
  if (x < scroll_x_) scroll_x_ = x;
  if (x > scroll_x_+width) scroll_x_ = std::max(0.f, x-width);
  scroll_x_ = std::min(scroll_x_, std::max(0.f, caret_x(value_.size())-width));
  blink_started_ = animation_time_;
}
void TextField::move_caret(std::size_t position, bool extend) {
  caret_ = position;
  if (!extend) anchor_ = caret_;
  reveal_caret();
}
void TextField::on_pointer(const PointerEvent& e) {
  if (e.cancel || e.up) { selecting_ = false; return; }
  if (!e.down && !(e.move && selecting_)) return;
  if (e.down) composition_.clear();
  const float x = e.x - rect_.x - 16 + scroll_x_;
  std::size_t chosen = 0;
  for (std::size_t i = 0; i < value_.size();) {
    const auto j = next(value_, i);
    if (x < (caret_x(i)+caret_x(j))/2) break;
    chosen = j;
    i = j;
  }
  move_caret(chosen, !e.down);
  if (e.down) selecting_ = true;
}
void TextField::replace_selection(std::string text) {
  validate_text(text);
  const auto lo = std::min(caret_, anchor_), hi = std::max(caret_, anchor_);
  if (value_.size()-(hi-lo)+text.size() > kMaxTextLen) return;
  const std::string before = value_;
  value_.replace(lo, hi-lo, text);
  caret_ = anchor_ = lo+text.size();
  label_progress_.animate(focused_ || !value_.empty() ? 1 : 0, 150,
                          motion::Curve::Standard, animation_time_);
  reveal_caret();
  if (value_ != before && on_change_) on_change_(value_);
}
void TextField::on_text(const TextEvent& e) {
  if (focused_ && !opt_.disabled) {
    composition_.clear();
    replace_selection(single_line(e.text));
  }
}
void TextField::on_composition(const CompositionEvent& e) {
  if (!focused_ || opt_.disabled) return;
  validate_text(e.text);
  if (value_.size()+e.text.size() > kMaxTextLen) return;
  composition_ = e.text;
  composition_start_ = character_index(composition_,e.start);
  const int remaining = int(composition_.size()-composition_start_);
  composition_end_ = composition_start_+character_index(composition_.substr(composition_start_),
      std::min(remaining,std::max(0,e.length)));
  blink_started_ = animation_time_;
}
std::optional<Rect> TextField::text_input_area() const {
  if (!focused_ || opt_.disabled || !opt_.visible) return {};
  const float extra = default_font().measure(std::string_view(composition_).substr(0,composition_end_),16).w;
  const float left = rect_.x+16, width = std::max(0.f,rect_.w-32);
  const float x = std::clamp(left+caret_x(caret_)+extra-scroll_x_,left,left+width);
  return Rect{x,rect_.y+(rect_.h-16)/2,1,rect_.h-(rect_.h-16)/2};
}
void TextField::on_key(const KeyEvent& e) {
  if (!focused_ || opt_.disabled) return;
  if (e.control && e.key == Key::A) {
    composition_.clear(); anchor_ = 0; caret_ = value_.size(); reveal_caret();
  } else if (e.control && (e.key == Key::C || e.key == Key::X)) {
    if (caret_ != anchor_) {
      const auto lo = std::min(caret_,anchor_), hi = std::max(caret_,anchor_);
      if (clipboard_write_(std::string_view(value_).substr(lo,hi-lo)) && e.key == Key::X)
        replace_selection("");
    }
  } else if (e.control && e.key == Key::V) {
    const std::string pasted = clipboard_read_();
    if (pasted.size() > kMaxTextLen) return;
    composition_.clear();
    replace_selection(single_line(pasted));
  } else if (!composition_.empty()) return;
  else if (e.key == Key::Left) {
    move_caret(!e.shift && caret_ != anchor_ ? std::min(caret_, anchor_) :
               e.control ? previous_word(value_,caret_) : previous(value_, caret_), e.shift);
  } else if (e.key == Key::Right) {
    move_caret(!e.shift && caret_ != anchor_ ? std::max(caret_, anchor_) :
               e.control ? next_word(value_,caret_) : next(value_, caret_), e.shift);
  } else if (e.key == Key::Home) move_caret(0, e.shift);
  else if (e.key == Key::End) move_caret(value_.size(), e.shift);
  else if (e.key == Key::Backspace) {
    if (caret_ == anchor_) anchor_ = e.control ? previous_word(value_,caret_) : previous(value_, caret_);
    replace_selection("");
  } else if (e.key == Key::Delete) {
    if (caret_ == anchor_) anchor_ = e.control ? next_word(value_,caret_) : next(value_, caret_);
    replace_selection("");
  } else if (e.key == Key::Enter && on_submit_) on_submit_(value_);
}
void TextField::paint(Renderer& r) {
  if (!opt_.visible) return;
  const float f = float(focus_.value(animation_time_));
  const float h = float(hover_.value(animation_time_));
  const float lp = float(label_progress_.value(animation_time_));
  Color border = mix(mix(colors::kOutline, colors::kOnSurface, .25f*h),
                     colors::kPrimary, f);
  // Split clips leave the floating-label notch transparent over any parent.
  const float label_px = 16-4*lp;
  const Size label = default_font().measure(label_, label_px);
  if (lp > 0 && !label_.empty()) {
    const float left = rect_.x+12, right = rect_.x+20+label.w*lp;
    r.clip_push({rect_.x, rect_.y, left-rect_.x, rect_.h});
    r.stroke_rect(rect_, border, 1+f, 4); r.clip_pop();
    r.clip_push({right, rect_.y, std::max(0.f, rect_.x+rect_.w-right), rect_.h});
    r.stroke_rect(rect_, border, 1+f, 4); r.clip_pop();
    r.clip_push({left, rect_.y+8*lp, right-left, std::max(0.f, rect_.h-8*lp)});
    r.stroke_rect(rect_, border, 1+f, 4); r.clip_pop();
  } else r.stroke_rect(rect_, border, 1+f, 4);
  const float label_y = rect_.y+(rect_.h-label.h)/2*(1-lp)-label.h/2*lp;
  default_font().draw(r, rect_.x+16, label_y, label_,
                     mix(colors::kOnSurfaceVariant, colors::kPrimary, f), label_px);
  const float text_h = default_font().measure("M",16).h;
  const float y = rect_.y+(rect_.h-text_h)/2;
  r.clip_push({rect_.x+16, rect_.y+4, std::max(0.f,rect_.w-32), rect_.h-8});
  if (caret_ != anchor_ && focused_ && composition_.empty()) {
    const float lo = caret_x(std::min(caret_,anchor_));
    const float hi = caret_x(std::max(caret_,anchor_));
    Color selection = colors::kPrimary; selection.a = 92;
    r.fill_rect({rect_.x+16+lo-scroll_x_, y, hi-lo, text_h}, selection);
  }
  const std::string displayed = value_.substr(0,caret_)+composition_+value_.substr(caret_);
  default_font().draw(r, rect_.x+16-scroll_x_, y, displayed, colors::kOnSurface,16);
  float composition_caret = 0;
  if (!composition_.empty()) {
    const float start = rect_.x+16+caret_x(caret_)-scroll_x_;
    const float w = default_font().measure(composition_,16).w;
    r.fill_rect({start,y+text_h,std::max(1.f,w),1},colors::kOnSurfaceVariant);
    composition_caret = default_font().measure(std::string_view(composition_).substr(0,composition_end_),16).w;
  }
  if (focused_ && std::fmod(std::max(0.0, animation_time_-blink_started_),1.0) < .5)
    r.fill_rect({rect_.x+16+caret_x(caret_)+composition_caret-scroll_x_, y, 2, text_h},colors::kPrimary);
  r.clip_pop();
}

ListView::ListView(float spacing, ControlOptions opt) : Control(std::move(opt)), spacing_(spacing) {
  if (!std::isfinite(spacing) || spacing < 0 || spacing > kMaxLayoutDim)
    throw std::invalid_argument("ListView spacing out of bounds");
}
void ListView::add(std::unique_ptr<Control> child) {
  if (children_.size() >= kMaxListItems) throw std::invalid_argument("ListView exceeds kMaxListItems");
  add_child(std::move(child));
}
Size ListView::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  return Control::intrinsic(opt_.width.value_or(max_w.value_or(0)),
                            opt_.height.value_or(max_h.value_or(0)));
}
void ListView::layout() {
  content_height_ = 0;
  bool first = true;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    if (!first) content_height_ += spacing_;
    Size s = child->intrinsic(rect_.w, {});
    if (!std::isfinite(s.h) || s.h < 0 || content_height_+s.h > kMaxLayoutDim)
      throw std::invalid_argument("ListView content height exceeds kMaxLayoutDim");
    content_height_ += s.h;
    first = false;
  }
  offset_ = std::clamp(offset_,0.f,std::max(0.f,content_height_-rect_.h));
  float y = rect_.y-offset_;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic(rect_.w,{});
    child->set_rect({rect_.x,y,rect_.w,s.h});
    child->layout();
    y += s.h+spacing_;
  }
}
void ListView::set_offset(float offset) {
  if (!std::isfinite(offset)) return;
  offset_ = std::clamp(offset,0.f,std::max(0.f,content_height_-rect_.h));
  layout();
}
Rect ListView::thumb_rect() const {
  const float track_h = std::max(0.f,rect_.h);
  const float height = std::min(track_h,std::max(32.f,track_h*rect_.h/std::max(1.f,content_height_)));
  const float y = rect_.y+(track_h-height)*offset_/std::max(1.f,content_height_-rect_.h);
  const float width = float(scrollbar_width_.value(animation_time_));
  return {rect_.x+rect_.w-width-2,y,width,height};
}
void ListView::activate_scrollbar() {
  scrollbar_alpha_.animate(hovered_ || dragging_ ? .64 : .48,100,motion::Curve::Standard,animation_time_);
  scrollbar_width_.animate(hovered_ || dragging_ ? 10 : 8,100,
                           motion::Curve::Standard,animation_time_);
  hide_at_ = animation_time_+.6;
}
void ListView::on_hover(bool on) {
  hovered_ = on;
  if (on) activate_scrollbar();
  else {
    scrollbar_width_.animate(8,100,motion::Curve::Standard,animation_time_);
    scrollbar_alpha_.animate(.48,100,motion::Curve::Standard,animation_time_);
    hide_at_ = animation_time_+.6;
  }
}
void ListView::tick(double now) {
  Control::tick(now);
  if (hide_at_ >= 0 && now >= hide_at_ && !hovered_ && !dragging_) {
    hide_at_ = -1;
    scrollbar_alpha_.animate(0,250,motion::Curve::Standard,now);
  }
}
bool ListView::on_scroll(const ScrollEvent& e) {
  if (!opt_.visible || opt_.disabled || !hit_test(e.x,e.y) || !std::isfinite(e.delta_y)) return false;
  set_offset(offset_-e.delta_y*40);
  activate_scrollbar();
  return true;
}
Control* ListView::hit_target(float x,float y) {
  if (!opt_.visible || opt_.disabled || !hit_test(x,y)) return nullptr;
  if (x >= rect_.x+rect_.w-16) return this;
  return Control::hit_target(x,y);
}
Control* ListView::hover_target(float x,float y) {
  if (!opt_.visible || opt_.disabled || !hit_test(x,y)) return nullptr;
  if (x >= rect_.x+rect_.w-16) return this;
  for (auto it = children_.rbegin(); it != children_.rend(); ++it)
    if (*it)
      if (auto* target = (*it)->hover_target(x,y)) return target;
  return nullptr;
}
void ListView::on_pointer(const PointerEvent& e) {
  if (e.cancel || e.up) {
    if (dragging_) {
      dragging_ = false;
      activate_scrollbar();
    }
    return;
  }
  if (!opt_.visible || opt_.disabled) return;
  if (e.down && e.x >= rect_.x+rect_.w-16 && content_height_ > rect_.h) {
    const Rect thumb = thumb_rect();
    if (e.y < thumb.y || e.y > thumb.y+thumb.h) {
      const float travel = rect_.h-thumb.h;
      if (travel > 0)
        set_offset((e.y-rect_.y-thumb.h/2)*(content_height_-rect_.h)/travel);
    }
    dragging_ = true; drag_y_ = e.y; drag_offset_ = offset_;
    activate_scrollbar();
  }
  if (e.move && dragging_) {
    const float travel = rect_.h-thumb_rect().h;
    if (travel > 0) set_offset(drag_offset_+(e.y-drag_y_)*(content_height_-rect_.h)/travel);
    activate_scrollbar();
  }
}
void ListView::paint(Renderer& r) {
  if (!opt_.visible) return;
  r.clip_push(rect_);
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    const Rect cr = child->rect();
    if (cr.y+cr.h > rect_.y && cr.y < rect_.y+rect_.h) child->paint(r);
  }
  if (content_height_ > rect_.h) {
    Color color = colors::kOnSurfaceVariant;
    color.a = std::uint8_t(std::lround(255*scrollbar_alpha_.value(animation_time_)));
    const Rect thumb = thumb_rect();
    if (color.a) r.fill_rect(thumb,color,thumb.w/2);
  }
  r.clip_pop();
}
}
