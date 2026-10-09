#include "opengl_renderer.hpp"
#include "saturn/limits.hpp"
#include <SDL3/SDL.h>
#include <stdexcept>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif
#include <GL/gl.h>

namespace saturn {
struct OpenGLRenderer::Impl {
  SDL_Window* window = nullptr; // not owned
  SDL_GLContext ctx = nullptr;  // owned
  int w = 0, h = 0;
};

OpenGLRenderer::OpenGLRenderer(void* sdl_window) : impl_(std::make_unique<Impl>()) {
  impl_->window = static_cast<SDL_Window*>(sdl_window);
  impl_->ctx = SDL_GL_CreateContext(impl_->window);
  if (!impl_->ctx) throw std::runtime_error(SDL_GetError());
  if (!SDL_GL_MakeCurrent(impl_->window, impl_->ctx))
    throw std::runtime_error(SDL_GetError());
  SDL_GetWindowSizeInPixels(impl_->window, &impl_->w, &impl_->h);
  glViewport(0, 0, impl_->w, impl_->h);
}

OpenGLRenderer::~OpenGLRenderer() {
  if (impl_ && impl_->ctx) {
    SDL_GL_DestroyContext(impl_->ctx);
    impl_->ctx = nullptr;
  }
}

void OpenGLRenderer::clear(Color c) {
  if (!impl_ || !impl_->ctx) return;
  SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
  glViewport(0, 0, impl_->w, impl_->h);
  glClearColor(c.r / 255.f, c.g / 255.f, c.b / 255.f, c.a / 255.f);
  glClear(GL_COLOR_BUFFER_BIT);
}

void OpenGLRenderer::fill_rect(Rect, Color, float) {}
void OpenGLRenderer::stroke_rect(Rect, Color, float, float) {}
void OpenGLRenderer::clip_push(Rect) {}
void OpenGLRenderer::clip_pop() {}

void OpenGLRenderer::flip() {
  if (!impl_ || !impl_->window) return;
  SDL_GL_SwapWindow(impl_->window);
}

void OpenGLRenderer::on_resize(int w, int h) {
  if (w < 0 || h < 0) return;
  if (static_cast<std::size_t>(w) > kMaxLayoutDim || static_cast<std::size_t>(h) > kMaxLayoutDim) return;
  impl_->w = w; impl_->h = h;
  if (impl_->ctx) {
    SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
    glViewport(0, 0, w, h);
  }
}
}
