#include "saturn/control.hpp"
#include "saturn/limits.hpp"
namespace saturn {
Control::Control(ControlOptions opt) : opt_(std::move(opt)) {}
void Control::set_options(ControlOptions opt) { opt_ = std::move(opt); }
const ControlOptions& Control::options() const { return opt_; }
Size Control::intrinsic(OptionalSize max_w, OptionalSize max_h) const {
  float w = opt_.width.value_or(max_w.value_or(0));
  float h = opt_.height.value_or(max_h.value_or(0));
  if (w > kMaxLayoutDim) w = static_cast<float>(kMaxLayoutDim);
  if (h > kMaxLayoutDim) h = static_cast<float>(kMaxLayoutDim);
  if (w < 0) w = 0; if (h < 0) h = 0;
  return {w, h};
}
}
