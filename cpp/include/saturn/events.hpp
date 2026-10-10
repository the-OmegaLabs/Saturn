#pragma once
#include <string>
#include <variant>
namespace saturn {
struct PointerEvent {
  float x = 0, y = 0;
  bool down = false;
  bool up = false;
  // Motion also drives hover when no button is held.
  bool move = false;
  bool cancel = false;
};
enum class Key { Other, Tab, Enter, Space, Backspace, Delete, Left, Right, Up, Down, Home, End, A, C, X, V, Escape };
struct KeyEvent {
  Key key = Key::Other;
  bool shift = false, control = false;
};
struct TextEvent { std::string text; };
struct CompositionEvent { std::string text; int start = 0, length = 0; };
struct ScrollEvent { float x = 0, y = 0, delta_y = 0; };
using InputEvent = std::variant<PointerEvent, KeyEvent, TextEvent, CompositionEvent, ScrollEvent>;
}
