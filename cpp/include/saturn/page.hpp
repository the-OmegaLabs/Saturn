#pragma once
#include "control.hpp"
#include <string>
namespace saturn {
class Renderer;
class Page : public Control {
public:
  Page();
  void set_title(std::string title);
  const std::string& title() const;
  void add(std::unique_ptr<Control> child);
  void update();
  bool layout_dirty() const;
  void layout(float width, float height, float padding = 40.f, float gap = 16.f);
  void paint(Renderer& r) override;
  void dispatch_pointer(const PointerEvent& e);
private:
  std::string title_;
  bool layout_dirty_ = true;
  // Deepest hit target under page subtree; not owning. Clear before remove if remove lands.
  Control* pointer_capture_ = nullptr;
};
}
