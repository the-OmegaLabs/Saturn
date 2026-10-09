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
  // Vertical column: padding + gap. Not a full flex engine.
  void layout(float width, float height, float padding = 40.f, float gap = 16.f);
  void paint(Renderer& r) override;
private:
  std::string title_;
  bool layout_dirty_ = true;
};
}
