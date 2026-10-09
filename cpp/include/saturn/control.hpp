#pragma once
#include "types.hpp"
#include "events.hpp"
#include <chrono>
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
  void draw(Renderer& r, Rect dst, Color tint);
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
protected:
  Pressable(std::function<void()> on_click, ControlOptions opt = {});
  bool pressed() const { return pressed_; }
  void set_pressed(bool v) { pressed_ = v; }
private:
  std::function<void()> on_click_;
  bool pressed_ = false;
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

// M3 filled: PRIMARY idle / PRIMARY_CONTAINER pressed.
class FilledButton final : public ButtonBase {
public:
  FilledButton(std::string label, std::function<void()> on_click, ControlOptions opt = {});
protected:
  void paint_background(Renderer& r) override;
  Color content_color() const override;
};

// M3 elevated (Python Button): SURFACE_CONTAINER_LOW bg, PRIMARY fg.
// leading_icon is a Material PNG path (e.g. "icons/add.png"); empty = no icon.
// Default is empty — demo passes "icons/add.png" explicitly when needed.
class ElevatedButton final : public ButtonBase {
public:
  ElevatedButton(std::string label, std::function<void()> on_click,
                 std::string icon_path = "", ControlOptions opt = {});
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
class Image final : public Control {
public:
  explicit Image(std::string path, ControlOptions opt = {});
  void set_tint(Color c);
  void clear_tint();
  bool loaded() const;
  Size intrinsic(OptionalSize max_w, OptionalSize max_h) const override;
  void paint(Renderer& r) override;
private:
  TextureImage image_;
  bool has_tint_ = false;
  Color tint_{255, 255, 255, 255};
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
  std::function<void(bool)> on_change_;
  TextureImage check_icon_;
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
private:
  bool value_ = false;
  std::function<void(bool)> on_change_;
};

// M3 ProgressRing: default 40×40, stroke 4, color PRIMARY. value in [0,1].
// Track = SDF annulus (SECONDARY_CONTAINER). Progress arc is segmented discs
// along the centerline (no rotated stroke / angular SDF yet) — pixel debt vs
// Python; see DEMO.md. Safety: segs capped at 180; value finite + clamped.
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

// Simple M3-ish dropdown: closed field (hint or selected text) + inline popup
// list when open (no animation / no page overlay). options capped by
// kMaxDropdownOptions; hint/key/text > kMaxTextBytes throw (no truncate).
// TextField/ListView still frozen elsewhere.
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
private:
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
};


// Overlay base for Page::show_dialog / pop_dialog. Barrier dialogs swallow
// outside clicks; non-barrier (SnackBar) let the page stay live.
class DialogControl : public Control {
public:
  bool barrier() const { return barrier_; }
  bool modal() const { return modal_; }
  // Called once when pushed onto the page overlay stack.
  virtual void on_shown();
  // Per-frame; SnackBar uses this for duration auto-dismiss.
  virtual void tick();
protected:
  DialogControl(bool barrier, bool modal = false);
  void dismiss();
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
  static constexpr float kContentPx = 14.f;
  static constexpr float kMinCardW = 280.f;
  static constexpr float kActionGap = 8.f;
  AlertDialog(std::string title, std::string content,
              std::vector<std::unique_ptr<Control>> actions,
              bool modal = false);
  void layout() override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
  void on_pointer(const PointerEvent& e) override;
private:
  bool point_in_card(float x, float y) const;
  std::string title_;
  std::string content_;
  Rect card_rect_{};
};

// M3 SnackBar: bottom bar (INVERSE_SURFACE), optional action TextButton.
// Non-barrier; queued under kMaxSnackBarQueue (separate from kMaxDialogDepth).
// duration_ms in (0, kMaxSnackBarDurationMs]; with a non-empty action label the
// bar persists until action/dismiss (Python persist default).
// Message / action label over kMaxTextBytes → throw.
class SnackBar final : public DialogControl {
public:
  static constexpr float kPad = 24.f;
  static constexpr float kMargin = 16.f;
  static constexpr float kMinH = 48.f;
  static constexpr float kTextPx = 14.f;
  static constexpr float kRadius = 4.f;
  SnackBar(std::string message, std::string action_label = "",
           std::function<void()> on_action = {},
           int duration_ms = 4000);
  void on_shown() override;
  void tick() override;
  void layout() override;
  void paint(Renderer& r) override;
  bool hit_test(float x, float y) const override;
private:
  std::string message_;
  std::string action_label_;
  std::function<void()> on_action_;
  int duration_ms_ = 4000;
  bool has_deadline_ = false;
  std::chrono::steady_clock::time_point deadline_{};
  Rect bar_rect_{};
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
