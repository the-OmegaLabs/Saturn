#pragma once
#include "types.hpp"
#include "events.hpp"
#include <cstdint>
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

// Shared click press/release + on_click. Subclasses own hit_test.
class Pressable : public Control {
public:
  void on_pointer(const PointerEvent& e) override;
protected:
  Pressable(std::function<void()> on_click, ControlOptions opt = {});
  bool pressed() const { return pressed_; }
  void set_pressed(bool v) { pressed_ = v; }
private:
  std::function<void()> on_click_;
  bool pressed_ = false;
};

// M3 labeled button skeleton: measure / paint label(+optional leading icon) /
// round hit / corner radius. Style via paint_background + content_color.
class ButtonBase : public Pressable {
public:
  static constexpr float kDefaultCornerRadius = 20.f;
  void set_corner_radius(float radius);
  float corner_radius() const;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
protected:
  ButtonBase(std::string label, std::function<void()> on_click,
             std::string leading_icon, ControlOptions opt = {});
  virtual void paint_background(Renderer& r) = 0;
  virtual Color content_color() const = 0;
  const std::string& label() const { return label_; }
  const std::string& leading_icon() const { return icon_; }
private:
  std::string label_;
  std::string icon_;
  float corner_radius_ = kDefaultCornerRadius;
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

// M3 filled: PRIMARY idle / PRIMARY_CONTAINER pressed.
class FilledButton final : public ButtonBase {
public:
  FilledButton(std::string label, std::function<void()> on_click, ControlOptions opt = {});
protected:
  void paint_background(Renderer& r) override;
  Color content_color() const override;
};

// M3 elevated (Python Button): SURFACE_CONTAINER_LOW bg, PRIMARY fg.
// leading_icon is Inter text glyph (e.g. "+"); empty skips icon slot.
class ElevatedButton final : public ButtonBase {
public:
  ElevatedButton(std::string label, std::function<void()> on_click,
                 std::string icon = "+", ControlOptions opt = {});
protected:
  void paint_background(Renderer& r) override;
  Color content_color() const override;
};

// M3 outlined: no fill (pressed SURFACE_CONTAINER), OUTLINE_VARIANT stroke.
class OutlinedButton final : public ButtonBase {
public:
  OutlinedButton(std::string label, std::function<void()> on_click, ControlOptions opt = {});
protected:
  void paint_background(Renderer& r) override;
  Color content_color() const override;
};

// M3 IconButton: side 40, icon 24. Loads a white+alpha PNG (Material glyph
// raster) and tints with theme tokens — not Inter ♥ pretending to be Material.
class IconButton final : public Pressable {
public:
  static constexpr float kSide = 40.f;
  static constexpr float kIconPx = 24.f;
  // icon_path: PNG under assets/ (e.g. "icons/favorite.png"). Caps: path /
  // file bytes / decode dim same as Image.
  IconButton(std::string icon_path, std::function<void()> on_click,
             ControlOptions opt = {});
  ~IconButton() override;
  IconButton(const IconButton&) = delete;
  IconButton& operator=(const IconButton&) = delete;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
private:
  void ensure_loaded() const;
  void ensure_texture(Renderer& r);
  void release_texture();
  std::string path_;
  mutable std::vector<std::uint8_t> rgba_;
  mutable int src_w_ = 0;
  mutable int src_h_ = 0;
  mutable bool tried_load_ = false;
  mutable bool load_ok_ = false;
  void* tex_ = nullptr;
  Renderer* tex_r_ = nullptr;
};

// PNG Image via stb_image. Optional tint (multiply). BoxFit.CONTAIN when both
// width and height are set on ControlOptions. Path/decode/dim failures throw
// (no silent empty paint); see kMaxImageDecodeDim / kMaxImageFileBytes.
class Image final : public Control {
public:
  explicit Image(std::string path, ControlOptions opt = {});
  ~Image() override;
  Image(const Image&) = delete;
  Image& operator=(const Image&) = delete;
  void set_tint(Color c);
  void clear_tint();
  bool loaded() const;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
private:
  void ensure_loaded() const;
  void ensure_texture(Renderer& r);
  void release_texture();
  std::string path_;
  mutable std::vector<std::uint8_t> rgba_;
  mutable int src_w_ = 0;
  mutable int src_h_ = 0;
  mutable bool tried_load_ = false;
  mutable bool load_ok_ = false;
  bool has_tint_ = false;
  Color tint_{255, 255, 255, 255};
  void* tex_ = nullptr;
  Renderer* tex_r_ = nullptr;
};

// M3 Checkbox: 18×18 box radius 2, active PRIMARY, optional label.
class Checkbox final : public Control {
public:
  static constexpr float kBox = 18.f;
  static constexpr float kBoxRadius = 2.f;
  static constexpr float kLabelGap = 8.f;
  static constexpr float kLabelPx = 14.f;
  Checkbox(std::string label, bool value = false,
           std::function<void(bool)> on_change = {}, ControlOptions opt = {});
  bool value() const;
  void set_value(bool v);
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  void on_pointer(const PointerEvent& e) override;
private:
  std::string label_;
  bool value_ = false;
  std::function<void(bool)> on_change_;
  bool pressed_ = false;
};

// M3 Slider: intrinsic ~300×48, active PRIMARY. Click + drag (pointer move
// while captured). divisions>0 snaps to steps; ctor rejects divisions outside
// [0, kMaxSliderDivisions]. set_value / apply_value reject non-finite.
class Slider final : public Control {
public:
  static constexpr float kDefaultWidth = 300.f;
  static constexpr float kDefaultHeight = 48.f;
  Slider(float min_v, float max_v, int divisions = 0,
         std::function<void(float)> on_change = {}, ControlOptions opt = {});
  float value() const;
  void set_value(float v);
  float min_value() const { return min_; }
  float max_value() const { return max_; }
  int divisions() const { return divisions_; }
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  void on_pointer(const PointerEvent& e) override;
private:
  float value_from_x(float x) const;
  void apply_value(float v);
  float min_ = 0.f;
  float max_ = 100.f;
  int divisions_ = 0;
  float value_ = 0.f;
  std::function<void(float)> on_change_;
  bool dragging_ = false;
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
