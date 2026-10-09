#pragma once
namespace saturn {
struct PointerEvent {
  float x = 0, y = 0;
  bool down = false;
  bool up = false;
  // Motion while a button is held (for Slider drag). Ignored unless captured.
  bool move = false;
};
}
