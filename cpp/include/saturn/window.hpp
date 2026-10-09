#pragma once
#include <memory>
#include <string>
namespace saturn {
class Renderer;
// Owns SDL window. Creates/destroys paired Renderer.
class Window {
public:
  Window(const std::string& title, int w, int h);
  ~Window();
  Window(const Window&) = delete;
  Window& operator=(const Window&) = delete;
  bool poll_quit(); // process events; true if quit
  Renderer& renderer();
  void swap();
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
}
