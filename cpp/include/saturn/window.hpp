#pragma once
#include "events.hpp"
#include "types.hpp"
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
  std::vector<InputEvent> take_input_events();
  void set_title(const std::string& title);
  void set_text_input_area(std::optional<Rect> area);

  // LOGICAL client size (SDL_GetWindowSize). Matches pointer event coords;
  // use for layout / hit-testing.
  int client_width() const;
  int client_height() const;

  // PIXEL framebuffer size (SDL_GetWindowSizeInPixels). Matches GL viewport /
  // SATURN_SHOT. Equals client_* only at 100% DPI.
  // No width()/height() aliases — always pick client_* (layout) or drawable_* (GL/shot).
  int drawable_width() const;
  int drawable_height() const;

  // Construction intent is the ctor `w`,`h` (logical client). After pin_client,
  // client_* is the live source of truth — no separate requested_* API.

  Renderer& renderer();
  void swap();
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
}
