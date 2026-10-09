#pragma once
#include "types.hpp"
#include <memory>
#include <string>
#include <string_view>
namespace saturn {
class Renderer;

// TrueType/OpenType face (stb_truetype). Explicit API - no kwargs.
// Bitmap 5x7 is not for pixel parity; demo path requires a loaded Font.
class Font {
public:
  // Load TTF/OTF from path. Path length capped by kMaxPathBytes; file by kMaxFontFileBytes.
  // Throws on missing/invalid font.
  static Font load(std::string path);

  // SATURN_FONT_PATH, then <base>/assets/Inter-Regular.ttf, then cwd relatives.
  // Throws if none load (fail loud - do not silently fall back to bitmap for demo).
  static Font load_default();

  Font(Font&&) noexcept;
  Font& operator=(Font&&) noexcept;
  ~Font();

  Font(const Font&) = delete;
  Font& operator=(const Font&) = delete;

  const std::string& path() const;

  // px_size clamped to [kMinFontPx, kMaxFontPx]; non-finite throws.
  Size measure(std::string_view text, float px_size) const;
  float ascent(float px_size) const;   // pixels above baseline
  float descent(float px_size) const;  // pixels below baseline (positive)
  float line_height(float px_size) const;

  // Top-left of the text box (ascent above baseline). Throws if text.size() > kMaxTextLen.
  void draw(Renderer& r, float x, float y, std::string_view text, Color color, float px_size) const;

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
  explicit Font(std::unique_ptr<Impl> impl);
};

// Process-wide default for Text / FilledButton. Throws if unset.
Font& default_font();
void set_default_font(Font font);
// Load default and install; returns false on failure (message via what of caught).
bool try_init_default_font();
} // namespace saturn
