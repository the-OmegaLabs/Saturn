#pragma once
#include <cstdint>
#include <optional>
#include <string>
namespace saturn {
struct Color { std::uint8_t r,g,b,a; };
struct Rect { float x,y,w,h; };
struct Size { float w,h; };
using OptionalSize = std::optional<float>; // nullopt = unconstrained; clamp via limits.hpp
struct ControlOptions {
  bool visible = true;
  bool disabled = false;
  float opacity = 1.f;
  OptionalSize width;
  OptionalSize height;
  // open fields: typed/opaque only — no untyped dump
  std::optional<std::int64_t> data_i64;
  std::optional<std::string> data_str;
};
}
