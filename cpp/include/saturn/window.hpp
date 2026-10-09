#pragma once
#include "events.hpp"
#include <memory>
#include <string>
#include <vector>
namespace saturn {
class Renderer;
class Window {
public:
  Window(const std::string& title, int w, int h);
  ~Window();
  Window(const Window&) = delete;
  Window& operator=(const Window&) = delete;
  bool poll_quit();
  bool consume_resized(int* out_w, int* out_h);
  std::vector<PointerEvent> take_pointer_events();
  int width() const;
  int height() const;
  Renderer& renderer();
  void swap();
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
}
