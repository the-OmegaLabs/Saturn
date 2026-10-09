#pragma once
#include "types.hpp"
#include "limits.hpp"
#include <cmath>
#include <algorithm>
namespace saturn {

inline float clamp_f(float v, float lo, float hi) {
  return (std::max)(lo, (std::min)(hi, v));
}

// Soft max for corner radius used by hit tests (matches renderer soft caps).
inline float effective_corner_radius_for(const Rect& r, float radius) {
  if (!std::isfinite(radius) || radius <= 0.f) return 0.f;
  if (radius > kMaxCornerRadius) radius = kMaxCornerRadius;
  float half = 0.5f * (std::min)(r.w, r.h);
  if (half < 0.f) half = 0.f;
  return clamp_f(radius, 0.f, half);
}

// Signed distance to rounded rect; negative = inside. Matches SDF fill path.
inline float sd_round_rect(float px, float py, const Rect& r, float radius) {
  float rad = effective_corner_radius_for(r, radius);
  float cx = r.x + r.w * 0.5f;
  float cy = r.y + r.h * 0.5f;
  float hx = r.w * 0.5f - rad;
  float hy = r.h * 0.5f - rad;
  if (hx < 0.f) hx = 0.f;
  if (hy < 0.f) hy = 0.f;
  float dx = std::fabs(px - cx) - hx;
  float dy = std::fabs(py - cy) - hy;
  float ax = (std::max)(dx, 0.f);
  float ay = (std::max)(dy, 0.f);
  return std::sqrt(ax * ax + ay * ay) + (std::min)((std::max)(dx, dy), 0.f) - rad;
}

inline bool hit_round_rect(float x, float y, const Rect& r, float radius) {
  if (!(r.w > 0.f && r.h > 0.f)) return false;
  if (!std::isfinite(x) || !std::isfinite(y)) return false;
  if (!std::isfinite(r.x) || !std::isfinite(r.y) || !std::isfinite(r.w) || !std::isfinite(r.h))
    return false;
  float rad = effective_corner_radius_for(r, radius);
  if (rad <= 0.f) {
    return x >= r.x && y >= r.y && x < r.x + r.w && y < r.y + r.h;
  }
  return sd_round_rect(x, y, r, rad) <= 0.f;
}

} // namespace saturn
