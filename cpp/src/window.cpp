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
  SDL_Window* win = nullptr;
  std::unique_ptr<OpenGLRenderer> renderer;
  int w = 0, h = 0;
  bool resized = false;
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
  try {
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
    impl_->win = SDL_CreateWindow(title.c_str(), w, h, SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE);
    if (!impl_->win) throw std::runtime_error(SDL_GetError());
    impl_->renderer = std::make_unique<OpenGLRenderer>(impl_->win);
    impl_->w = w;
    impl_->h = h;
  } catch (...) {
    if (impl_->win) {
      SDL_DestroyWindow(impl_->win);
      impl_->win = nullptr;
    }
    if (g_sdl_users.fetch_sub(1) == 1) SDL_Quit();
    throw;
  }
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
    if (e.type == SDL_EVENT_WINDOW_RESIZED) {
      int nw = e.window.data1;
      int nh = e.window.data2;
      if (nw > 0 && nh > 0 &&
          static_cast<std::size_t>(nw) <= kMaxLayoutDim &&
          static_cast<std::size_t>(nh) <= kMaxLayoutDim) {
        impl_->w = nw;
        impl_->h = nh;
        impl_->resized = true;
        impl_->renderer->on_resize(nw, nh);
      }
    }
  }
  return false;
}

bool Window::consume_resized(int* out_w, int* out_h) {
  if (!impl_->resized) return false;
  impl_->resized = false;
  if (out_w) *out_w = impl_->w;
  if (out_h) *out_h = impl_->h;
  return true;
}

int Window::width() const { return impl_->w; }
int Window::height() const { return impl_->h; }
Renderer& Window::renderer() { return *impl_->renderer; }
void Window::swap() { impl_->renderer->flip(); }
}
