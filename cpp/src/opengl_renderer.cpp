#include "opengl_renderer.hpp"
#include "saturn/limits.hpp"
#include <SDL3/SDL.h>
#include <stdexcept>
namespace saturn {
struct OpenGLRenderer::Impl {
  SDL_Window* window = nullptr; // not owned
  SDL_GLContext ctx = nullptr;  // owned
  int w = 0, h = 0;
};
OpenGLRenderer::OpenGLRenderer(void* sdl_window) : impl_(new Impl) {
  impl_->window = static_cast<SDL_Window*>(sdl_window);
  impl_->ctx = SDL_GL_CreateContext(impl_->window);
  if (!impl_->ctx) throw std::runtime_error(SDL_GetError());
  SDL_GetWindowSizeInPixels(impl_->window, &impl_->w, &impl_->h);
}
OpenGLRenderer::~OpenGLRenderer() {
  if (impl_ && impl_->ctx) SDL_GL_DestroyContext(impl_->ctx);
  delete impl_;
}
void OpenGLRenderer::clear(Color c) {
  // GL clear — dense stub for ①
  (void)c;
  // full GL calls land in ②; ① only needs flip path wired
}
void OpenGLRenderer::fill_rect(Rect, Color, float) {}
void OpenGLRenderer::stroke_rect(Rect, Color, float, float) {}
void OpenGLRenderer::clip_push(Rect) {}
void OpenGLRenderer::clip_pop() {}
void OpenGLRenderer::flip() { SDL_GL_SwapWindow(impl_->window); }
void OpenGLRenderer::on_resize(int w, int h) {
  if (w < 0 || h < 0) return;
  if (static_cast<std::size_t>(w) > kMaxLayoutDim || static_cast<std::size_t>(h) > kMaxLayoutDim) return;
  impl_->w = w; impl_->h = h;
}
}
