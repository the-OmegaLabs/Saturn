#pragma once
#include "events.hpp"
#include <memory>
#include <string>
#include <vector>
namespace saturn {
class Renderer;
class Window {
public:
  // `w`,`h` are the desired CLIENT / drawable size (SDL CreateWindow semantics).
  // After create, logical client size is pinned; width()/height() report pixel
  // drawable size (GL viewport / SATURN_SHOT).
  Window(const std::string& title, int w, int h);
  ~Window();
  Window(const Window&) = delete;
  Window& operator=(const Window&) = delete;
  bool poll_quit();
  bool consume_resized(int* out_w, int* out_h);
  std::vector<PointerEvent> take_pointer_events();
  void set_title(const std::string& title);
  // Drawable / framebuffer size in pixels (matches GL viewport / SATURN_SHOT).
  int width() const;
  int height() const;
  // Client size requested at construction (SDL logical units).
  int requested_width() const;
  int requested_height() const;
  Renderer& renderer();
  void swap();
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
}
