#include "saturn/page.hpp"
#include "saturn/limits.hpp"
#include "saturn/renderer.hpp"
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
  if (overlays_.size() >= kMaxDialogDepth)
    throw std::runtime_error("dialog stack exceeds kMaxDialogDepth");
  for (const auto& o : overlays_) {
    if (o.get() == dialog.get()) return;
  }
  DialogControl* raw = dialog.get();
  dialog->attach(this, this);
  overlays_.push_back(std::move(dialog));
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
      if (pointer_capture_ && overlay_contains(d, pointer_capture_))
        pointer_capture_ = nullptr;
      overlays_.erase(it);
      layout_dirty_ = true;
      break;
    }
  }
}

void Page::tick() {
  // Copy pointers: SnackBar::tick may call pop_dialog (deferred).
  std::vector<DialogControl*> live;
  live.reserve(overlays_.size());
  for (auto& o : overlays_) {
    if (o) live.push_back(o.get());
  }
  for (DialogControl* d : live) d->tick();
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
  for (auto& o : overlays_) {
    if (o && o->options().visible) o->paint(r);
  }
  r.clip_pop();
}

void Page::dispatch_pointer(const PointerEvent& e) {
  if (e.down) {
    pointer_capture_ = nullptr;
    // Overlays top-most first. Barrier always claims; non-barrier only on hit.
    for (auto it = overlays_.rbegin(); it != overlays_.rend(); ++it) {
      DialogControl* d = it->get();
      if (!d || !d->options().visible || d->options().disabled) continue;
      Control* target = d->hit_target(e.x, e.y);
      if (target) {
        pointer_capture_ = target;
        target->on_pointer(e);
        flush_pending_dialog_pops();
        return;
      }
      if (d->barrier()) {
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
      pointer_capture_ = target;
      target->on_pointer(e);
      break;
    }
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
}
