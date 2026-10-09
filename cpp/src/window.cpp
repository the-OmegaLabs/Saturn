#include "saturn/window.hpp"
#include "opengl_renderer.hpp"
#include "saturn/limits.hpp"
#include <SDL3/SDL.h>
#include <atomic>
#include <stdexcept>

namespace saturn {
namespace {
std::atomic<int> g_sdl_users{0};
}

struct Window::Impl {
  SDL_Window* win = nullptr; // owned
  std::unique_ptr<OpenGLRenderer> renderer;
};

Window::Window(const std::string& title, int w, int h) : impl_(std::make_unique<Impl>()) {
  if (w <= 0 || h <= 0 || static_cast<std::size_t>(w) > kMaxLayoutDim || static_cast<std::size_t>(h) > kMaxLayoutDim)
    throw std::invalid_argument("window size out of bounds");
  if (g_sdl_users.fetch_add(1) == 0) {
    if (!SDL_Init(SDL_INIT_VIDEO)) {
      g_sdl_users.fetch_sub(1);
      throw std::runtime_error(SDL_GetError());
    }
  }
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
  impl_->win = SDL_CreateWindow(title.c_str(), w, h, SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE);
  if (!impl_->win) {
    if (g_sdl_users.fetch_sub(1) == 1) SDL_Quit();
    throw std::runtime_error(SDL_GetError());
  }
  impl_->renderer = std::make_unique<OpenGLRenderer>(impl_->win);
}

Window::~Window() {
  impl_->renderer.reset();
  if (impl_->win) {
    SDL_DestroyWindow(impl_->win);
    impl_->win = nullptr;
  }
  if (g_sdl_users.fetch_sub(1) == 1) SDL_Quit();
}

bool Window::poll_quit() {
  SDL_Event e;
  while (SDL_PollEvent(&e)) {
    if (e.type == SDL_EVENT_QUIT) return true;
    if (e.type == SDL_EVENT_WINDOW_RESIZED)
      impl_->renderer->on_resize(e.window.data1, e.window.data2);
  }
  return false;
}

Renderer& Window::renderer() { return *impl_->renderer; }
void Window::swap() { impl_->renderer->flip(); }
}
