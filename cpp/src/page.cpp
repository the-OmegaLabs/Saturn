#include "saturn/page.hpp"
#include "saturn/limits.hpp"
#include "saturn/renderer.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace saturn {
namespace {
float clamp_pad(float v) {
  if (!std::isfinite(v) || v < 0.f) return 0.f;
  if (v > float(kMaxLayoutDim)) return float(kMaxLayoutDim);
  return v;
}
} // namespace
Page::Page() : Control({}) {}
void Page::set_title(std::string title) {
  if (title.size() > kMaxTextBytes) title.resize(kMaxTextBytes);
  title_ = std::move(title);
}
const std::string& Page::title() const { return title_; }
void Page::set_bgcolor(Color c) { bgcolor_ = c; }
Color Page::bgcolor() const { return bgcolor_; }
void Page::set_padding(float pad) {
  padding_ = clamp_pad(pad);
  layout_dirty_ = true;
}
float Page::padding() const { return padding_; }
void Page::set_spacing(float gap) {
  spacing_ = clamp_pad(gap);
  layout_dirty_ = true;
}
float Page::spacing() const { return spacing_; }
void Page::add(std::unique_ptr<Control> child) {
  if (!child) return;
  if (children_.size() >= kMaxChildren) throw std::runtime_error("too many children");
  child->attach(this, this);
  children_.push_back(std::move(child));
  layout_dirty_ = true;
}
void Page::update() { layout_dirty_ = true; }
bool Page::layout_dirty() const { return layout_dirty_; }

bool Page::overlay_contains(Control* root, Control* target) const {
  for (Control* c = target; c != nullptr; c = c->parent_) {
    if (c == root) return true;
  }
  return false;
}

void Page::show_dialog(std::unique_ptr<DialogControl> dialog) {
  if (!dialog) throw std::invalid_argument("show_dialog: null dialog");
  // Separate budgets: barrier → kMaxDialogDepth; non-barrier (SnackBar) →
  // kMaxSnackBarQueue. Shared overlays_.size() must not gate either.
  std::size_t dialog_n = 0;
  std::size_t snack_n = 0;
  for (const auto& o : overlays_) {
    if (!o) continue;
    if (o->barrier()) ++dialog_n;
    else ++snack_n;
  }
  if (dialog->barrier()) {
    if (dialog_n >= kMaxDialogDepth)
      throw std::runtime_error("dialog stack exceeds kMaxDialogDepth");
  } else {
    if (snack_n >= kMaxSnackBarQueue)
      throw std::runtime_error("snackbar queue exceeds kMaxSnackBarQueue");
  }
  for (const auto& o : overlays_) {
    if (o.get() == dialog.get()) return;
  }
  DialogControl* raw = dialog.get();
  if (dialog->barrier()) {
    if (active_menu_) active_menu_->set_open(false);
    if (pointer_capture_) {
      pointer_capture_->on_pointer({0,0,false,false,false,true});
      pointer_capture_ = nullptr;
    }
    if (hovered_) hovered_->on_hover(false);
    hovered_ = nullptr;
    set_focus(nullptr);
  }
  dialog->attach(this, this);
  overlays_.push_back(std::move(dialog));
  raw->tick(animation_time_);
  raw->on_shown();
  layout_dirty_ = true;
}

void Page::pop_dialog(DialogControl* dialog) {
  if (dialog == nullptr) {
    if (overlays_.empty()) return;
    dialog = overlays_.back().get();
  }
  for (DialogControl* p : pending_pops_) {
    if (p == dialog) return;
  }
  // Only queue if still on the stack.
  bool found = false;
  for (const auto& o : overlays_) {
    if (o.get() == dialog) { found = true; break; }
  }
  if (!found) return;
  pending_pops_.push_back(dialog);
}

void Page::flush_pending_dialog_pops() {
  if (pending_pops_.empty()) return;
  std::vector<DialogControl*> pending = std::move(pending_pops_);
  pending_pops_.clear();
  for (DialogControl* d : pending) {
    for (auto it = overlays_.begin(); it != overlays_.end(); ++it) {
      if (it->get() != d) continue;
      if (!d->closing()) {
        if (pointer_capture_ && overlay_contains(d,pointer_capture_)) {
          pointer_capture_->on_pointer({0,0,false,false,false,true});
          pointer_capture_ = nullptr;
        }
        if (hovered_ && overlay_contains(d,hovered_)) {
          hovered_->on_hover(false);
          hovered_ = nullptr;
        }
        if (focused_ && overlay_contains(d,focused_)) set_focus(nullptr);
        d->begin_dismiss();
      }
      if (!d->ready_to_remove()) break;
      if (pointer_capture_ && overlay_contains(d, pointer_capture_))
        pointer_capture_ = nullptr;
      if (hovered_ && overlay_contains(d, hovered_)) hovered_ = nullptr;
      if (focused_ && overlay_contains(d, focused_)) set_focus(nullptr);
      if (active_menu_ && overlay_contains(d, active_menu_)) active_menu_ = nullptr;
      overlays_.erase(it);
      layout_dirty_ = true;
      break;
    }
  }
}

void Page::tick(double now) {
  Control::tick(now);
  reconcile_input();
  // Copy pointers: SnackBar::tick may call pop_dialog (deferred).
  std::vector<DialogControl*> live;
  live.reserve(overlays_.size());
  for (auto& o : overlays_) {
    if (o) live.push_back(o.get());
  }
  for (DialogControl* d : live) d->tick(now);
  for (DialogControl* d : live)
    if (d->ready_to_remove()) pop_dialog(d);
  flush_pending_dialog_pops();
}

void Page::layout(float width, float height) {
  if (!(width > 0) || !(height > 0)) {
    layout_dirty_ = false;
    return;
  }
  if (width > kMaxLayoutDim) width = float(kMaxLayoutDim);
  if (height > kMaxLayoutDim) height = float(kMaxLayoutDim);
  float padding = padding_;
  float gap = spacing_;
  set_rect(Rect{0, 0, width, height});
  float inner_w = width - padding * 2.f;
  if (inner_w < 0) inner_w = 0;
  float y = padding;
  for (auto& child : children_) {
    if (!child || !child->options().visible) continue;
    Size s = child->intrinsic(inner_w, {});
    if (s.w > inner_w) s.w = inner_w;
    child->set_rect(Rect{padding, y, s.w, s.h});
    child->layout(); // Row/Column position their own kids
    y += s.h + gap;
  }
  // Overlays fill the page (scrim / bottom bar use full client rect).
  for (auto& o : overlays_) {
    if (!o || !o->options().visible) continue;
    o->set_rect(Rect{0, 0, width, height});
    o->layout();
  }
  layout_dirty_ = false;
}

void Page::paint(Renderer& r) {
  r.clip_push(rect_);
  Control::paint(r);
  if (active_menu_) active_menu_->paint_menu(r);
  for (auto& o : overlays_) {
    if (o && o->options().visible) o->paint(r);
  }
  r.clip_pop();
}

void Page::dispatch_pointer(const PointerEvent& e) {
  reconcile_input();
  if (!opt_.visible || opt_.disabled) return;
  if (e.cancel) {
    if (pointer_capture_) pointer_capture_->on_pointer(e);
    pointer_capture_ = nullptr;
    if (hovered_) hovered_->on_hover(false);
    hovered_ = nullptr;
    set_focus(nullptr);
    flush_pending_dialog_pops();
    return;
  }
  update_hover(e.x, e.y);
  if (e.down) {
    if (pointer_capture_) pointer_capture_->on_pointer({0,0,false,false,false,true});
    pointer_capture_ = nullptr;
    if (active_menu_) {
      if (active_menu_->menu_hit_test(e.x,e.y)) {
        pointer_capture_ = active_menu_;
        active_menu_->on_pointer(e);
        return;
      }
      if (!active_menu_->hit_test(e.x,e.y)) active_menu_->set_open(false);
    }
    // Overlays top-most first. Barrier always claims; non-barrier only on hit.
    for (auto it = overlays_.rbegin(); it != overlays_.rend(); ++it) {
      DialogControl* d = it->get();
      if (!d || !d->options().visible || d->options().disabled) continue;
      Control* target = d->hit_target(e.x, e.y);
      if (target) {
        set_focus(target->focusable() ? target : nullptr);
        pointer_capture_ = target;
        target->on_pointer(e);
        flush_pending_dialog_pops();
        return;
      }
      if (d->barrier()) {
        set_focus(nullptr);
        // Should not happen — AlertDialog hit_test covers the page — but swallow.
        pointer_capture_ = d;
        d->on_pointer(e);
        flush_pending_dialog_pops();
        return;
      }
      // SnackBar miss: fall through to lower overlays / page.
    }
    for (auto it = children_.rbegin(); it != children_.rend(); ++it) {
      Control* c = it->get();
      if (!c || !c->options().visible || c->options().disabled) continue;
      Control* target = c->hit_target(e.x, e.y);
      if (!target) continue;
      set_focus(target->focusable() ? target : nullptr);
      pointer_capture_ = target;
      target->on_pointer(e);
      break;
    }
    if (!pointer_capture_) set_focus(nullptr);
    flush_pending_dialog_pops();
    return;
  }
  if (e.move) {
    if (pointer_capture_) pointer_capture_->on_pointer(e);
    flush_pending_dialog_pops();
    return;
  }
  if (e.up) {
    if (pointer_capture_) {
      Control* c = pointer_capture_;
      pointer_capture_ = nullptr;
      c->on_pointer(e);
    }
    flush_pending_dialog_pops();
  }
}
void Page::update_hover(float x, float y) {
  Control* target = nullptr;
  bool blocked = false;
  for (auto it = overlays_.rbegin(); it != overlays_.rend(); ++it) {
    auto* d = it->get();
    if (!d || !d->options().visible || d->options().disabled) continue;
    target = d->hover_target(x, y);
    if (target || d->barrier()) { blocked = true; break; }
  }
  if (!target && !blocked) target = Control::hover_target(x, y);
  if (target == hovered_) return;
  if (hovered_) hovered_->on_hover(false);
  hovered_ = target;
  if (hovered_) hovered_->on_hover(true);
}
void Page::set_focus(Control* control) {
  if (focused_ == control) return;
  if (focused_) focused_->on_focus(false);
  focused_ = control;
  if (focused_) focused_->on_focus(true);
}
void Page::collect_focusable(Control* root, std::vector<Control*>& out) const {
  if (!root || !root->opt_.visible || root->opt_.disabled) return;
  if (auto* dialog = dynamic_cast<DialogControl*>(root); dialog && dialog->closing()) return;
  if (root->focusable()) out.push_back(root);
  for (auto& child : root->children_) collect_focusable(child.get(), out);
}
void Page::dispatch_key(const KeyEvent& e) {
  reconcile_input();
  if (!opt_.visible || opt_.disabled) return;
  if (e.key == Key::Tab) {
    std::vector<Control*> controls;
    Control* modal = nullptr;
    for (auto it = overlays_.rbegin(); it != overlays_.rend(); ++it)
      if ((*it)->barrier() && (*it)->options().visible) { modal = it->get(); break; }
    if (modal) collect_focusable(modal, controls);
    else {
      collect_focusable(this, controls);
      for (auto& overlay : overlays_) collect_focusable(overlay.get(), controls);
    }
    if (controls.empty()) { set_focus(nullptr); return; }
    auto it = std::find(controls.begin(), controls.end(), focused_);
    std::size_t i = it == controls.end() ? (e.shift ? controls.size()-1 : 0) :
        (std::size_t(it-controls.begin()) + (e.shift ? controls.size()-1 : 1)) % controls.size();
    set_focus(controls[i]);
  } else if (e.key == Key::Escape && !overlays_.empty()) {
    if (!overlays_.back()->modal()) pop_dialog();
  } else if (e.key == Key::Escape && active_menu_) {
    active_menu_->set_open(false);
  } else if (focused_ && focused_->options().visible && !focused_->options().disabled) {
    for (auto it = overlays_.rbegin(); it != overlays_.rend(); ++it)
      if ((*it)->barrier() && !overlay_contains(it->get(),focused_)) return;
    focused_->on_key(e);
  }
  flush_pending_dialog_pops();
}
void Page::dispatch_text(const TextEvent& e) {
  reconcile_input();
  if (focused_ && focused_->options().visible && !focused_->options().disabled)
    focused_->on_text(e);
}
void Page::dispatch_composition(const CompositionEvent& e) {
  reconcile_input();
  if (focused_ && input_enabled(focused_)) focused_->on_composition(e);
}
std::optional<Rect> Page::text_input_area() const {
  return input_enabled(focused_) ? focused_->text_input_area() : std::nullopt;
}
void Page::dispatch_scroll(const ScrollEvent& e) {
  reconcile_input();
  if (!opt_.visible || opt_.disabled) return;
  if (active_menu_ && active_menu_->on_scroll(e)) return;
  Control* target = nullptr;
  for (auto it = overlays_.rbegin(); it != overlays_.rend(); ++it) {
    auto* d = it->get();
    if (!d || !d->options().visible || d->options().disabled) continue;
    target = d->hit_target(e.x, e.y);
    if (target) break;
    if (d->barrier()) return;
  }
  if (!target) target = hit_target(e.x, e.y);
  for (auto* c = target; c != nullptr; c = c->parent_)
    if (c->on_scroll(e)) break;
}
void Page::set_active_menu(Dropdown* menu) {
  if (active_menu_ && active_menu_ != menu) active_menu_->set_open(false);
  active_menu_ = menu;
}
void Page::clear_active_menu(Dropdown* menu) {
  if (active_menu_ == menu) active_menu_ = nullptr;
}
bool Page::input_enabled(Control* control) const {
  if (!control) return false;
  for (auto* c = control; c; c = c->parent_)
    if (!c->opt_.visible || c->opt_.disabled) return false;
  return true;
}
void Page::reconcile_input() {
  if (pointer_capture_ && !input_enabled(pointer_capture_)) {
    pointer_capture_->on_pointer({0,0,false,false,false,true});
    pointer_capture_ = nullptr;
  }
  if (hovered_ && !input_enabled(hovered_)) {
    hovered_->on_hover(false);
    hovered_ = nullptr;
  }
  if (focused_ && !input_enabled(focused_)) set_focus(nullptr);
  if (active_menu_ && !input_enabled(active_menu_)) {
    active_menu_->set_open(false);
    active_menu_ = nullptr;
  }
}
}
