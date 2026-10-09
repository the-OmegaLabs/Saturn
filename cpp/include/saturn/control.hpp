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
  // Row/Column: share leftover main-axis space equally among expand children.
  void set_expand(bool expand);
  bool expand() const;
  virtual Size intrinsic(OptionalSize max_w, OptionalSize max_h) const;
  // Position children from rect_. Default: recurse. Row/Column override.
  virtual void layout();
  virtual void paint(Renderer& r);
  virtual bool hit_test(float x, float y) const;
  // Deepest visible enabled control under (x,y); children back-to-front, then self.
  Control* hit_target(float x, float y);
  virtual void on_pointer(const PointerEvent& e);
  void set_rect(Rect rect);
  Rect rect() const;
protected:
  // Propagates page_ to existing subtree (so build-then-page.add works).
  void attach(Page* page, Control* parent);
  void add_child(std::unique_ptr<Control> child);
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
  explicit Text(std::string value, Color color = Color{0xff,0xff,0xff,0xff},
                 float size = 16.f, ControlOptions opt = {});
  void set_value(std::string value);
  const std::string& value() const;
  void set_size(float px);
  float size() const;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
private:
  std::string value_;
  Color color_;
  float size_ = 16.f;
};

class FilledButton final : public Control {
public:
  // Default corner radius 8px; renderer also clamps to kMaxCornerRadius / half min(w,h).
  static constexpr float kDefaultCornerRadius = 8.f;
  FilledButton(std::string label, std::function<void()> on_click, ControlOptions opt = {});
  void set_corner_radius(float radius);
  float corner_radius() const;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  // Same effective radius as paint (kMaxCornerRadius / half min(w,h)).
  bool hit_test(float x, float y) const override;
  void on_pointer(const PointerEvent& e) override;
private:
  std::string label_;
  std::function<void()> on_click_;
  float corner_radius_ = kDefaultCornerRadius;
  bool pressed_ = false;
};

// Vertical stack. Owns children via unique_ptr; spacing between visible kids.
// Cross-axis = horizontal (set_cross_axis_alignment). Default Start (Python Column).
class Column final : public Control {
public:
  explicit Column(float spacing = 0.f, ControlOptions opt = {});
  void add(std::unique_ptr<Control> child);
  void set_spacing(float spacing);
  float spacing() const;
  void set_cross_axis_alignment(CrossAxisAlignment align);
  CrossAxisAlignment cross_axis_alignment() const;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void layout() override;
private:
  float spacing_ = 0.f;
  CrossAxisAlignment cross_align_ = CrossAxisAlignment::Start;
};

// Horizontal stack. Owns children via unique_ptr; spacing between visible kids.
// Cross-axis = vertical (set_cross_axis_alignment). Default Center (Python Row).
class Row final : public Control {
public:
  explicit Row(float spacing = 0.f, ControlOptions opt = {});
  void add(std::unique_ptr<Control> child);
  void set_spacing(float spacing);
  float spacing() const;
  void set_cross_axis_alignment(CrossAxisAlignment align);
  CrossAxisAlignment cross_axis_alignment() const;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void layout() override;
private:
  float spacing_ = 0.f;
  CrossAxisAlignment cross_align_ = CrossAxisAlignment::Center;
};

// Box with padding/bgcolor/radius. Owns children; clips paint to bounds.
class Container final : public Control {
public:
  explicit Container(ControlOptions opt = {});
  void set_bgcolor(Color c);
  void set_padding(float pad);
  void set_corner_radius(float radius);
  void add(std::unique_ptr<Control> child);
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void layout() override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
private:
  Color bgcolor_{0,0,0,0};
  bool has_bg_ = false;
  float padding_ = 0.f;
  float corner_radius_ = 0.f;
};
}
