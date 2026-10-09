#pragma once
#include "types.hpp"
#include <memory>
#include <vector>
namespace saturn {
class Page;
class Renderer;
class Control {
  friend class Page;
public:
  explicit Control(ControlOptions opt = {});
  virtual ~Control() = default;
  Control(const Control&) = delete;
  Control& operator=(const Control&) = delete;
  void set_options(ControlOptions opt);
  const ControlOptions& options() const;
  virtual Size intrinsic(OptionalSize max_w, OptionalSize max_h) const;
  virtual void paint(Renderer& r);
  void set_rect(Rect rect);
  Rect rect() const;
protected:
  void attach(Page* page, Control* parent) { page_ = page; parent_ = parent; }
  ControlOptions opt_;
  Page* page_ = nullptr;
  Control* parent_ = nullptr;
  Rect rect_{};
  std::vector<std::unique_ptr<Control>> children_;
};

// Demo solid-color box. Size from ControlOptions width/height.
class ColorBox final : public Control {
public:
  ColorBox(Color color, ControlOptions opt = {});
  void paint(Renderer& r) override;
private:
  Color color_;
};
}
