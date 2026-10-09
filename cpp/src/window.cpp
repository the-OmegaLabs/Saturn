#include "saturn/window.hpp"
#include "opengl_renderer.hpp"
#include "saturn/limits.hpp"
#include <SDL3/SDL.h>
#include <atomic>
#include <stdexcept>
#include <string>

namespace saturn {
namespace {
std::atomic<int> g_sdl_users{0};
}

struct Window::Impl {
  SDL_Window* win = nullptr;
  std::unique_ptr<OpenGLRenderer> renderer;
  int w = 0, h = 0;           // pixel drawable
  int req_w = 0, req_h = 0;   // requested client (logical)
  bool resized = false;
  std::vector<PointerEvent> pointers;
};

namespace {
// SDL CreateWindow(w,h) sizes the CLIENT (logical) area — not Win32 outer.
// Pin logical client once; report pixel drawable via GetWindowSizeInPixels
// (equals logical at 100% DPI; larger under HiDPI).
void pin_client(SDL_Window* win, int want_w, int want_h, int* out_px_w, int* out_px_h) {
  int lw = 0, lh = 0;
  SDL_GetWindowSize(win, &lw, &lh);
  if (lw != want_w || lh != want_h) {
    if (!SDL_SetWindowSize(win, want_w, want_h))
      throw std::runtime_error(std::string("SDL_SetWindowSize: ") + SDL_GetError());
    SDL_PumpEvents();
    SDL_SyncWindow(win);
    SDL_GetWindowSize(win, &lw, &lh);
  }
  if (lw != want_w || lh != want_h) {
    throw std::runtime_error(
        "window client size mismatch: requested " + std::to_string(want_w) + "x" +
        std::to_string(want_h) + " got logical " + std::to_string(lw) + "x" +
        std::to_string(lh) + " (SDL sizes client; Python page.window uses outer)");
  }
  int pw = 0, ph = 0;
  SDL_GetWindowSizeInPixels(win, &pw, &ph);
  if (pw <= 0 || ph <= 0)
    throw std::runtime_error("window drawable pixel size invalid");
  *out_px_w = pw;
  *out_px_h = ph;
}
} // namespace

Window::Window(const std::string& title, int w, int h) : impl_(std::make_unique<Impl>()) {
  if (w <= 0 || h <= 0 || static_cast<std::size_t>(w) > kMaxLayoutDim || static_cast<std::size_t>(h) > kMaxLayoutDim)
    throw std::invalid_argument("window size out of bounds");
  if (g_sdl_users.fetch_add(1) == 0) {
    if (!SDL_Init(SDL_INIT_VIDEO)) {
      g_sdl_users.fetch_sub(1);
      throw std::runtime_error(SDL_GetError());
    }
  }
  impl_->req_w = w;
  impl_->req_h = h;
  try {
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
    // w,h = CLIENT/drawable intent (not Win32 outer). Python page.window uses outer.
    impl_->win = SDL_CreateWindow(title.c_str(), w, h, SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE);
    if (!impl_->win) throw std::runtime_error(SDL_GetError());
    pin_client(impl_->win, w, h, &impl_->w, &impl_->h);
    impl_->renderer = std::make_unique<OpenGLRenderer>(impl_->win);
    // Renderer ctor may re-query pixels; re-pin and refresh stored size.
    pin_client(impl_->win, w, h, &impl_->w, &impl_->h);
    impl_->renderer->on_resize(impl_->w, impl_->h);
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
    if (e.type == SDL_EVENT_WINDOW_RESIZED ||
        e.type == SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED) {
      int nw = 0, nh = 0;
      SDL_GetWindowSizeInPixels(impl_->win, &nw, &nh);
      if (nw > 0 && nh > 0 &&
          static_cast<std::size_t>(nw) <= kMaxLayoutDim &&
          static_cast<std::size_t>(nh) <= kMaxLayoutDim) {
        impl_->w = nw;
        impl_->h = nh;
        impl_->resized = true;
        impl_->renderer->on_resize(nw, nh);
      }
    }
    if (e.type == SDL_EVENT_MOUSE_BUTTON_DOWN || e.type == SDL_EVENT_MOUSE_BUTTON_UP) {
      if (e.button.button == SDL_BUTTON_LEFT) {
        PointerEvent pe;
        pe.x = float(e.button.x);
        pe.y = float(e.button.y);
        pe.down = e.type == SDL_EVENT_MOUSE_BUTTON_DOWN;
        pe.up = e.type == SDL_EVENT_MOUSE_BUTTON_UP;
        if (impl_->pointers.size() < kMaxEventQueue) impl_->pointers.push_back(pe);
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

std::vector<PointerEvent> Window::take_pointer_events() {
  std::vector<PointerEvent> out;
  out.swap(impl_->pointers);
  return out;
}

void Window::set_title(const std::string& title) {
  if (impl_->win) SDL_SetWindowTitle(impl_->win, title.c_str());
}
int Window::width() const { return impl_->w; }
int Window::height() const { return impl_->h; }
int Window::requested_width() const { return impl_->req_w; }
int Window::requested_height() const { return impl_->req_h; }
Renderer& Window::renderer() { return *impl_->renderer; }
void Window::swap() { impl_->renderer->flip(); }
}
