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
  int client_w = 0, client_h = 0;       // logical (SDL_GetWindowSize)
  int drawable_w = 0, drawable_h = 0;   // pixels (GetWindowSizeInPixels)
  int req_w = 0, req_h = 0;             // requested client at construction
  bool resized = false;
  std::vector<PointerEvent> pointers;
};

namespace {
// Pin LOGICAL client to want_*; fill out_* with both logical and pixel sizes.
// SDL_CreateWindow(w,h) sizes the client (logical) — not Win32 outer.
// Pixel drawable equals logical only at 100% DPI.
void pin_client(SDL_Window* win, int want_w, int want_h,
                int* out_client_w, int* out_client_h,
                int* out_px_w, int* out_px_h) {
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
  *out_client_w = lw;
  *out_client_h = lh;
  *out_px_w = pw;
  *out_px_h = ph;
}

void refresh_sizes(SDL_Window* win, int* client_w, int* client_h,
                   int* drawable_w, int* drawable_h) {
  int lw = 0, lh = 0, pw = 0, ph = 0;
  SDL_GetWindowSize(win, &lw, &lh);
  SDL_GetWindowSizeInPixels(win, &pw, &ph);
  if (lw > 0 && lh > 0 &&
      static_cast<std::size_t>(lw) <= kMaxLayoutDim &&
      static_cast<std::size_t>(lh) <= kMaxLayoutDim) {
    *client_w = lw;
    *client_h = lh;
  }
  if (pw > 0 && ph > 0 &&
      static_cast<std::size_t>(pw) <= kMaxLayoutDim &&
      static_cast<std::size_t>(ph) <= kMaxLayoutDim) {
    *drawable_w = pw;
    *drawable_h = ph;
  }
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
    // w,h = LOGICAL CLIENT (not Win32 outer, not necessarily pixels).
    impl_->win = SDL_CreateWindow(title.c_str(), w, h, SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE);
    if (!impl_->win) throw std::runtime_error(SDL_GetError());
    pin_client(impl_->win, w, h,
               &impl_->client_w, &impl_->client_h,
               &impl_->drawable_w, &impl_->drawable_h);
    impl_->renderer = std::make_unique<OpenGLRenderer>(impl_->win);
    // Renderer ctor may re-query; re-pin and refresh stored sizes.
    pin_client(impl_->win, w, h,
               &impl_->client_w, &impl_->client_h,
               &impl_->drawable_w, &impl_->drawable_h);
    impl_->renderer->on_resize(impl_->drawable_w, impl_->drawable_h);
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
      const int prev_cw = impl_->client_w;
      const int prev_ch = impl_->client_h;
      const int prev_dw = impl_->drawable_w;
      const int prev_dh = impl_->drawable_h;
      refresh_sizes(impl_->win,
                    &impl_->client_w, &impl_->client_h,
                    &impl_->drawable_w, &impl_->drawable_h);
      if (impl_->drawable_w != prev_dw || impl_->drawable_h != prev_dh) {
        impl_->renderer->on_resize(impl_->drawable_w, impl_->drawable_h);
      }
      if (impl_->client_w != prev_cw || impl_->client_h != prev_ch ||
          impl_->drawable_w != prev_dw || impl_->drawable_h != prev_dh) {
        impl_->resized = true;
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

bool Window::consume_resized(int* out_drawable_w, int* out_drawable_h) {
  if (!impl_->resized) return false;
  impl_->resized = false;
  if (out_drawable_w) *out_drawable_w = impl_->drawable_w;
  if (out_drawable_h) *out_drawable_h = impl_->drawable_h;
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
int Window::client_width() const { return impl_->client_w; }
int Window::client_height() const { return impl_->client_h; }
int Window::drawable_width() const { return impl_->drawable_w; }
int Window::drawable_height() const { return impl_->drawable_h; }
int Window::requested_width() const { return impl_->req_w; }
int Window::requested_height() const { return impl_->req_h; }
Renderer& Window::renderer() { return *impl_->renderer; }
void Window::swap() { impl_->renderer->flip(); }
}
