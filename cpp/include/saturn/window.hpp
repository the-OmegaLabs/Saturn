#pragma once
#include "events.hpp"
#include <memory>
#include <string>
#include <vector>
namespace saturn {
class Renderer;
class Window {
public:
  // `w`,`h` are the desired LOGICAL CLIENT size (SDL_CreateWindow semantics —
  // not Win32 outer chrome, not necessarily pixel framebuffer).
  Window(const std::string& title, int w, int h);
  ~Window();
  Window(const Window&) = delete;
  Window& operator=(const Window&) = delete;
  bool poll_quit();
  // Reports drawable (pixel) size after a resize; null out_* allowed as dirty flag.
  bool consume_resized(int* out_drawable_w, int* out_drawable_h);
  std::vector<PointerEvent> take_pointer_events();
  void set_title(const std::string& title);

  // LOGICAL client size (SDL_GetWindowSize). Matches pointer event coords;
  // use for layout / hit-testing.
  int client_width() const;
  int client_height() const;

  // PIXEL framebuffer size (SDL_GetWindowSizeInPixels). Matches GL viewport /
  // SATURN_SHOT. Equals client_* only at 100% DPI.
  int drawable_width() const;
  int drawable_height() const;

  // Back-compat aliases → drawable_* (GL/shot). Prefer explicit client_/drawable_.
  int width() const { return drawable_width(); }
  int height() const { return drawable_height(); }

  // Client size requested at construction (logical).
  int requested_width() const;
  int requested_height() const;

  Renderer& renderer();
  void swap();
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
}
