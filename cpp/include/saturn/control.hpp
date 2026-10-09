#pragma once
#include "types.hpp"
#include "events.hpp"
#include <functional>
#include <memory>
#include <string>
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
  virtual bool hit_test(float x, float y) const;
  virtual void on_pointer(const PointerEvent& e);
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

class ColorBox final : public Control {
public:
  ColorBox(Color color, ControlOptions opt = {});
  void paint(Renderer& r) override;
private:
  Color color_;
};

class Text final : public Control {
public:
  explicit Text(std::string value, Color color = Color{0xff,0xff,0xff,0xff}, ControlOptions opt = {});
  void set_value(std::string value);
  const std::string& value() const;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
private:
  std::string value_;
  Color color_;
};

class FilledButton final : public Control {
public:
  FilledButton(std::string label, std::function<void()> on_click, ControlOptions opt = {});
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
  void on_pointer(const PointerEvent& e) override;
private:
  std::string label_;
  std::function<void()> on_click_;
  bool pressed_ = false;
};
}
