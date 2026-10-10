#pragma once
#include "types.hpp"
#include "events.hpp"
#include "motion.hpp"
#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <string_view>
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
  virtual Control* hit_target(float x, float y);
  virtual Control* hover_target(float x, float y);
  virtual bool accepts_hover() const { return false; }
  virtual void on_hover(bool on);
  virtual void tick(double now);
  virtual void on_pointer(const PointerEvent& e);
  virtual bool focusable() const { return false; }
  virtual void on_focus(bool focused);
  virtual void on_key(const KeyEvent& e);
  virtual void on_text(const TextEvent& e);
  virtual void on_composition(const CompositionEvent& e);
  virtual std::optional<Rect> text_input_area() const { return {}; }
  virtual bool on_scroll(const ScrollEvent& e);
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
  double animation_time_ = motion::now();
};

// Shared PNG decode + GPU upload + destroy. Used by Image, IconButton,
// Checkbox check mark, Elevated leading icon. Path/file/dim caps fail loud.
class TextureImage {
public:
  explicit TextureImage(std::string path);
  ~TextureImage();
  TextureImage(const TextureImage&) = delete;
  TextureImage& operator=(const TextureImage&) = delete;
  void ensure_loaded() const;
  void* ensure_texture(Renderer& r);
  void release_texture();
  // radius: SDF rounded mask (0 = sharp). Caps via renderer / clamp_radius.
  void draw(Renderer& r, Rect dst, Color tint, float radius = 0.f);
  bool loaded() const { return load_ok_; }
  int src_w() const { return src_w_; }
  int src_h() const { return src_h_; }
  const std::string& path() const { return path_; }
private:
  std::string path_;
  mutable std::vector<std::uint8_t> rgba_;
  mutable int src_w_ = 0;
  mutable int src_h_ = 0;
  mutable bool tried_load_ = false;
  mutable bool load_ok_ = false;
  void* tex_ = nullptr;
  Renderer* tex_r_ = nullptr;
};

// Shared click press/release + on_click. Subclasses own hit_test.
class Pressable : public Control {
public:
  void on_pointer(const PointerEvent& e) override;
  bool accepts_hover() const override { return true; }
  void on_hover(bool on) override;
  void tick(double now) override;
  bool focusable() const override { return true; }
  void on_focus(bool focused) override;
  void on_key(const KeyEvent& e) override;
protected:
  Pressable(std::function<void()> on_click, ControlOptions opt = {});
  bool pressed() const { return pressed_; }
  void set_pressed(bool v) { pressed_ = v; }
  bool hovered() const { return hovered_; }
  bool focused() const { return focused_; }
  virtual void on_pressed(float x, float y);
  virtual void on_released();
  void paint_state_layer(Renderer& r, Rect bounds, Color color, float radius);
  motion::StateLayer state_layer_;
private:
  std::function<void()> on_click_;
  bool pressed_ = false;
  bool hovered_ = false;
  bool focused_ = false;
};

// M3 labeled button skeleton: measure / paint label(+optional leading PNG) /
// round hit / corner radius. Style via paint_background + content_color.
class ButtonBase : public Pressable {
public:
  static constexpr float kDefaultCornerRadius = 20.f;
  ~ButtonBase() override;
  void set_corner_radius(float radius);
  float corner_radius() const;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
protected:
  // leading_icon_path: Material PNG under assets/ (empty = no icon).
  ButtonBase(std::string label, std::function<void()> on_click,
             std::string leading_icon_path, ControlOptions opt = {});
  virtual void paint_background(Renderer& r) = 0;
  virtual Color content_color() const = 0;
  const std::string& label() const { return label_; }
  bool has_leading_icon() const { return static_cast<bool>(leading_); }
private:
  std::string label_;
  std::unique_ptr<TextureImage> leading_;
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

// Brand vector mark. No bitmap decode/upload; renderer draws an analytic GPU shape.
class SaturnLogo final : public Control {
public:
  explicit SaturnLogo(Color color, ControlOptions opt = {});
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
private:
  Color color_;
};

// Single-line UTF-8 editor. Owns bounded text; callbacks receive the current value.
class TextField final : public Control {
public:
  TextField(std::string label, std::function<void(const std::string&)> on_change = {},
            std::function<void(const std::string&)> on_submit = {}, ControlOptions opt = {});
  const std::string& value() const { return value_; }
  void set_value(std::string value);
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  bool accepts_hover() const override { return true; }
  bool focusable() const override { return true; }
  void on_hover(bool on) override;
  void on_focus(bool on) override;
  void on_pointer(const PointerEvent& e) override;
  void on_key(const KeyEvent& e) override;
  void on_text(const TextEvent& e) override;
  void on_composition(const CompositionEvent& e) override;
  std::optional<Rect> text_input_area() const override;
  // Host clipboard operations; callbacks own any captured state.
  void set_clipboard_handlers(std::function<std::string()> read,
                              std::function<bool(std::string_view)> write);
private:
  void replace_selection(std::string text);
  void move_caret(std::size_t position, bool extend);
  float caret_x(std::size_t position) const;
  void reveal_caret();
  std::string label_, value_;
  std::string composition_;
  std::size_t composition_start_ = 0, composition_end_ = 0;
  std::function<std::string()> clipboard_read_;
  std::function<bool(std::string_view)> clipboard_write_;
  std::function<void(const std::string&)> on_change_, on_submit_;
  std::size_t caret_ = 0, anchor_ = 0;
  float scroll_x_ = 0;
  double blink_started_ = 0;
  bool focused_ = false, selecting_ = false;
  motion::Tween focus_, hover_, label_progress_;
};

// Owns capped children; draws visible rows directly with no scroll tile cache.
class ListView final : public Control {
public:
  explicit ListView(float spacing = 4, ControlOptions opt = {});
  void add(std::unique_ptr<Control> child);
  float scroll_offset() const { return offset_; }
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void layout() override;
  void paint(Renderer& r) override;
  Control* hit_target(float x, float y) override;
  Control* hover_target(float x, float y) override;
  bool on_scroll(const ScrollEvent& e) override;
  bool accepts_hover() const override { return true; }
  void on_hover(bool on) override;
  void on_pointer(const PointerEvent& e) override;
  void tick(double now) override;
private:
  Rect thumb_rect() const;
  void set_offset(float offset);
  void activate_scrollbar();
  float spacing_ = 4, offset_ = 0, content_height_ = 0;
  float drag_y_ = 0, drag_offset_ = 0;
  bool hovered_ = false, dragging_ = false;
  double hide_at_ = -1;
  motion::Tween scrollbar_alpha_, scrollbar_width_{8};
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
// Idle elevation=1 soft shadow ≈ painting.draw_shadow ambient+key
// (Python3 round blur/dy: e=1 → 2/1/dy=0; stacked fills; no blur kernel/FBO).
// leading_icon is a Material PNG path (e.g. "icons/add.png"); empty = no icon.
// Default is empty — demo passes "icons/add.png" explicitly when needed.
class ElevatedButton final : public ButtonBase {
public:
  ElevatedButton(std::string label, std::function<void()> on_click,
                 std::string icon_path = "", ControlOptions opt = {});
  void on_hover(bool on) override;
protected:
  void on_pressed(float x, float y) override;
  void on_released() override;
  void paint_background(Renderer& r) override;
  Color content_color() const override;
private:
  motion::Tween elevation_{1};
};

// M3 outlined: no fill (pressed SURFACE_CONTAINER), OUTLINE_VARIANT stroke.
class OutlinedButton final : public ButtonBase {
public:
  OutlinedButton(std::string label, std::function<void()> on_click, ControlOptions opt = {});
protected:
  void paint_background(Renderer& r) override;
  Color content_color() const override;
};


// M3 TextButton: no fill (pressed SURFACE_CONTAINER), PRIMARY label. Dialog Cancel.
class TextButton final : public ButtonBase {
public:
  TextButton(std::string label, std::function<void()> on_click, ControlOptions opt = {});
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
  // icon_path: PNG under assets/ (e.g. "icons/favorite.png"). Caps via TextureImage.
  IconButton(std::string icon_path, std::function<void()> on_click,
             ControlOptions opt = {});
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
private:
  TextureImage image_;
};

// PNG Image via TextureImage (stb_image). Optional tint (multiply).
// BoxFit.CONTAIN when both width and height are set on ControlOptions.
// Path/decode/dim failures throw (no silent empty paint).
// border_radius: SDF textured round (demo Image uses 8). Non-finite throws;
// otherwise clamp_radius / kMaxCornerRadius (no unbounded path).
class Image final : public Control {
public:
  enum class Fit { Fill, Contain };
  explicit Image(std::string path, ControlOptions opt = {}, float border_radius = 0.f);
  void set_tint(Color c);
  void clear_tint();
  void set_border_radius(float radius);
  float border_radius() const;
  void set_fit(Fit fit) { fit_ = fit; }
  bool loaded() const;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
private:
  TextureImage image_;
  bool has_tint_ = false;
  Color tint_{255, 255, 255, 255};
  float border_radius_ = 0.f;
  Fit fit_ = Fit::Fill;
};

// M3 Checkbox: 18×18 box radius 2, active PRIMARY, optional label.
// Check mark is Material check.png (TextureImage), not a geometric scribble.
// Press/click via Pressable (no hand-rolled pointer).
class Checkbox final : public Pressable {
public:
  static constexpr float kBox = 18.f;
  static constexpr float kBoxRadius = 2.f;
  static constexpr float kLabelGap = 8.f;
  static constexpr float kLabelPx = 14.f;
  static constexpr float kCheckPx = 14.f;
  Checkbox(std::string label, bool value = false,
           std::function<void(bool)> on_change = {}, ControlOptions opt = {});
  bool value() const;
  void set_value(bool v);
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
private:
  std::string label_;
  bool value_ = false;
  motion::Tween value_progress_;
  std::function<void(bool)> on_change_;
  TextureImage check_icon_;
};

// M3 Slider: intrinsic ~300×48, active PRIMARY. Click + drag (pointer move
// while captured). divisions>0 snaps to steps; ctor rejects divisions outside
// [0, kMaxSliderDivisions]. set_value / apply_value reject non-finite.
class Slider final : public Pressable {
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
  void on_key(const KeyEvent& e) override;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  void on_pointer(const PointerEvent& e) override;
private:
  float value_from_x(float x) const;
  void on_pressed(float x, float y) override;
  void on_released() override;
  void apply_value(float v);
  float min_ = 0.f;
  float max_ = 100.f;
  int divisions_ = 0;
  float value_ = 0.f;
  std::function<void(float)> on_change_;
  bool dragging_ = false;
  motion::Tween thumb_press_;
};

// M3 Switch: track 52×32 inside 52×40 hit box; no label required.
// Toggle via Pressable; active track PRIMARY, inactive SURFACE_CONTAINER_HIGHEST.
class Switch final : public Pressable {
public:
  static constexpr float kTrackW = 52.f;
  static constexpr float kTrackH = 32.f;
  static constexpr float kHeight = 40.f;
  Switch(bool value = false, std::function<void(bool)> on_change = {},
         ControlOptions opt = {});
  bool value() const;
  void set_value(bool v);
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  void on_pointer(const PointerEvent& e) override;
private:
  void animate_value();
  void on_pressed(float x, float y) override;
  void on_released() override;
  bool value_ = false;
  std::function<void(bool)> on_change_;
  motion::Tween position_, color_, size_, thumb_press_;
  float drag_start_x_ = 0;
  double drag_start_progress_ = 0;
  bool dragged_ = false;
};

// M3 ProgressRing: default 40×40, stroke 4, color PRIMARY. value in [0,1].
// Track + progress via Renderer::stroke_arc (angular SDF, round caps); track
// uses Python-style gap. value finite + clamped to [0,1].
class ProgressRing final : public Control {
public:
  static constexpr float kSide = 40.f;
  static constexpr float kStroke = 4.f;
  explicit ProgressRing(float value = 0.f, ControlOptions opt = {});
  float value() const;
  void set_value(float v);
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
private:
  float value_ = 0.f;
};


// Dropdown option row (key + display text). Used by Dropdown.
struct DropdownOption {
  std::string key;
  std::string text;
};

// Outlined field + animated page-level popup. Options capped by
// kMaxDropdownOptions; hint/key/text > kMaxTextBytes throw (no truncate).
class Dropdown final : public Control {
public:
  static constexpr float kDefaultWidth = 180.f;
  static constexpr float kFieldHeight = 56.f;
  static constexpr float kTextPx = 16.f;
  static constexpr float kItemHeight = 48.f;
  static constexpr float kPadH = 16.f;
  static constexpr float kRadius = 4.f;
  Dropdown(std::string hint, std::vector<DropdownOption> options,
           std::function<void(const std::string& key)> on_select = {},
           ControlOptions opt = {});
  bool is_open() const;
  const std::string& value() const; // selected key; empty if none
  const std::string& selected_text() const;
  void set_value(std::string key); // empty clears; unknown key throws
  void set_open(bool open);
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
  void on_pointer(const PointerEvent& e) override;
  bool accepts_hover() const override { return true; }
  bool focusable() const override { return true; }
  void on_hover(bool on) override;
  void on_focus(bool on) override;
  void on_key(const KeyEvent& e) override;
  bool on_scroll(const ScrollEvent& e) override;
  void tick(double now) override;
  void paint_menu(Renderer& r);
  bool menu_hit_test(float x, float y) const;
private:
  void pick_option(int index);
  Rect field_rect() const;
  Rect menu_rect() const;
  int hit_option(float x, float y) const; // -1 none
  std::string hint_;
  std::vector<DropdownOption> options_;
  std::function<void(const std::string& key)> on_select_;
  std::string value_;
  std::string selected_text_;
  bool open_ = false;
  bool pressed_ = false;
  int press_option_ = -1; // -2 = field, -1 = none, >=0 = option index
  motion::Tween menu_progress_, menu_timeline_, focus_progress_, hover_progress_;
  bool menu_closing_ = false;
  double menu_close_at_ = -1;
  float menu_offset_ = 0;
  int keyboard_index_ = 0;
};


// Overlay base for Page::show_dialog / pop_dialog. Barrier dialogs swallow
// outside clicks; non-barrier (SnackBar) let the page stay live.
class DialogControl : public Control {
public:
  bool barrier() const { return barrier_; }
  bool modal() const { return modal_; }
  // Called once when pushed onto the page overlay stack.
  virtual void on_shown();
  virtual void begin_dismiss();
  bool closing() const { return closing_; }
  bool ready_to_remove() const { return closing_ && animation_time_ >= close_at_; }
  Control* hit_target(float x, float y) override;
  // Per-frame; SnackBar uses this for duration auto-dismiss.
  void tick(double now) override;
protected:
  DialogControl(bool barrier, bool modal = false);
  void dismiss();
  bool closing_ = false;
  double close_at_ = -1;
private:
  bool barrier_ = true;
  bool modal_ = false;
};

// M3 AlertDialog: scrim + centered card (pad 24, inset 40, radius 28).
// title/content strings; actions are owned buttons (≤ kMaxDialogActions).
// Text over kMaxTextBytes / actions oversize → throw (no truncate).
class AlertDialog final : public DialogControl {
public:
  static constexpr float kPad = 24.f;
  static constexpr float kInset = 40.f;
  static constexpr float kRadius = 28.f;
  static constexpr float kTitlePx = 24.f;
  static constexpr float kContentPx = 16.f;
  static constexpr float kMinCardW = 280.f;
  static constexpr float kActionGap = 8.f;
  AlertDialog(std::string title, std::string content,
              std::vector<std::unique_ptr<Control>> actions,
              bool modal = false);
  void layout() override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
  void on_pointer(const PointerEvent& e) override;
  void on_shown() override;
  void begin_dismiss() override;
private:
  bool point_in_card(float x, float y) const;
  std::string title_;
  std::string content_;
  Rect card_rect_{};
  motion::Tween reveal_, timeline_;
};

// M3 SnackBar: bottom bar (INVERSE_SURFACE), optional action TextButton.
// Non-barrier; queued under kMaxSnackBarQueue (separate from kMaxDialogDepth).
// duration_ms in (0, kMaxSnackBarDurationMs]; with a non-empty action label the
// bar persists until action/dismiss (Python persist default).
// Message / action label over kMaxTextBytes → throw.
class SnackBar final : public DialogControl {
public:
  static constexpr float kPad = 24.f;
  static constexpr float kMargin = 0.f;
  static constexpr float kMinH = 48.f;
  static constexpr float kTextPx = 14.f;
  static constexpr float kRadius = 4.f;
  SnackBar(std::string message, std::string action_label = "",
           std::function<void()> on_action = {},
           int duration_ms = 4000);
  void on_shown() override;
  void begin_dismiss() override;
  void tick(double now) override;
  void layout() override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
private:
  std::string message_;
  std::string action_label_;
  std::function<void()> on_action_;
  int duration_ms_ = 4000;
  bool has_deadline_ = false;
  double deadline_ = 0;
  Rect bar_rect_{};
  motion::Tween reveal_;
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
