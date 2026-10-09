#pragma once
#include "control.hpp"
#include <string>
#include <vector>
namespace saturn {
class Renderer;
class Page : public Control {
public:
  Page();
  void set_title(std::string title);
  const std::string& title() const;
  void set_bgcolor(Color c);
  Color bgcolor() const;
  void set_padding(float pad);
  float padding() const;
  void set_spacing(float gap);
  float spacing() const;
  void add(std::unique_ptr<Control> child);
  void update();
  bool layout_dirty() const;
  // Uses page padding_/spacing_ when args omitted (defaults match setters).
  void layout(float width, float height);
  void paint(Renderer& r) override;
  void dispatch_pointer(const PointerEvent& e);
  // Overlay stack (AlertDialog / SnackBar). Depth capped by kMaxDialogDepth.
  // Ownership transfers to Page; pops are deferred until after pointer dispatch
  // so action on_click cannot UAF the button mid-handler.
  void show_dialog(std::unique_ptr<DialogControl> dialog);
  void pop_dialog(DialogControl* dialog = nullptr);
  // Per-frame: SnackBar deadlines + flush deferred pops.
  void tick();
private:
  void flush_pending_dialog_pops();
  bool overlay_contains(Control* root, Control* target) const;
  std::string title_;
  Color bgcolor_{0x14, 0x12, 0x18, 0xff}; // colors::kSurface
  float padding_ = 40.f;
  float spacing_ = 16.f;
  bool layout_dirty_ = true;
  // Deepest hit target under page subtree; not owning. Clear before remove if remove lands.
  Control* pointer_capture_ = nullptr;
  std::vector<std::unique_ptr<DialogControl>> overlays_;
  std::vector<DialogControl*> pending_pops_;
};
}
