#pragma once
#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>

namespace saturn::motion {
enum class Curve {
  Linear, Standard, StandardAccelerate, StandardDecelerate,
  Emphasized, EmphasizedAccelerate, EmphasizedDecelerate, SwitchOvershoot
};
inline double now() {
  return std::chrono::duration<double>(
      std::chrono::steady_clock::now().time_since_epoch()).count();
}
// Same Newton/bisection solver and control points as saturn/animation.py.
inline double ease(Curve curve, double t) {
  t = std::clamp(t, 0.0, 1.0);
  if (t == 0.0 || t == 1.0 || curve == Curve::Linear) return t;
  double x1 = .2, y1 = 0, x2 = 0, y2 = 1;
  switch (curve) {
    case Curve::StandardAccelerate: x1 = .3; x2 = 1; break;
    case Curve::StandardDecelerate: x1 = 0; break;
    case Curve::Emphasized: x1 = .3; break;
    case Curve::EmphasizedAccelerate: x1 = .3; x2 = .8; y2 = .15; break;
    case Curve::EmphasizedDecelerate: x1 = .05; y1 = .7; x2 = .1; break;
    case Curve::SwitchOvershoot: x1 = .175; y1 = .885; x2 = .32; y2 = 1.275; break;
    default: break;
  }
  auto axis = [](double u, double a, double b) {
    const double v = 1 - u;
    return 3*v*v*u*a + 3*v*u*u*b + u*u*u;
  };
  auto deriv = [](double u, double a, double b) {
    return 3*(1-u)*(1-u)*a + 6*(1-u)*u*(b-a) + 3*u*u*(1-b);
  };
  double u = t;
  bool converged = true;
  for (int i = 0; i < 8; ++i) {
    const double dx = deriv(u, x1, x2);
    if (std::abs(dx) < 1e-7) { converged = false; break; }
    const double candidate = u - (axis(u, x1, x2) - t) / dx;
    if (candidate < 0 || candidate > 1) { converged = false; break; }
    u = candidate;
  }
  if (!converged) {
    double lo = 0, hi = 1;
    for (int i = 0; i < 20; ++i) {
      u = (lo + hi) / 2;
      if (axis(u, x1, x2) < t) lo = u;
      else hi = u;
    }
    u = (lo + hi) / 2;
  }
  return axis(u, y1, y2);
}

// Fixed storage per animated scalar; retarget from the current sampled value.
class Tween {
public:
  explicit Tween(double initial = 0) : start_(initial), target_(initial) {}
  double value(double time) const {
    if (duration_ == 0 || time >= started_ + duration_) return target_;
    // Python interpolate() clamps eased endpoints, including overshoot curves.
    const double p = std::clamp(ease(curve_, (time-started_)/duration_), 0.0, 1.0);
    return start_ + (target_ - start_) * p;
  }
  void reset(double value) { start_ = target_ = value; duration_ = 0; }
  void animate(double target, double milliseconds, Curve curve, double time) {
    if (!std::isfinite(target) || !std::isfinite(milliseconds) ||
        !std::isfinite(time) || milliseconds < 0)
      throw std::invalid_argument("invalid tween arguments");
    start_ = value(time);
    target_ = target;
    started_ = time;
    duration_ = start_ == target_ ? 0 : milliseconds / 1000;
    curve_ = curve;
  }
private:
  double start_ = 0, target_ = 0, started_ = 0, duration_ = 0;
  Curve curve_ = Curve::Linear;
};

struct StateLayer {
  Tween hover, press_alpha, ripple;
  float origin_x = 0, origin_y = 0;
  double press_started = 0, release_deadline = -1;
  double ripple_ms = 200, press_ms = 75, minimum_ms = 0, fade_ms = 100;
  void set_hover(bool on, double time) {
    hover.animate(on ? .08 : 0, 15, Curve::Linear, time);
  }
  void press(float x, float y, double time) {
    origin_x = x; origin_y = y;
    press_started = time;
    release_deadline = -1;
    ripple.reset(0);
    ripple.animate(1, ripple_ms, Curve::Standard, time);
    press_alpha.animate(.12, press_ms, Curve::Linear, time);
  }
  void release(double time) {
    const double minimum_end = press_started + minimum_ms / 1000;
    if (time < minimum_end) release_deadline = minimum_end;
    else press_alpha.animate(0, fade_ms, Curve::Linear, time);
  }
  void tick(double time) {
    if (release_deadline >= 0 && time >= release_deadline) {
      release_deadline = -1;
      press_alpha.animate(0, fade_ms, Curve::Linear, time);
    }
  }
};
}
