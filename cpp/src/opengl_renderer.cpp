#include "opengl_renderer.hpp"
#include "saturn/limits.hpp"
#include <SDL3/SDL.h>
#include <stdexcept>
#include <vector>
#include <cmath>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif
#include <GL/gl.h>

// Minimal GL 1.1 path for phase-2 fill (compat profile via SDL attrs if needed).
// Core 3.3 would need shaders; for skeleton demo we request compat-friendly clear+rect.

namespace saturn {
namespace {
using PFNGLGENBUFFERSPROC = void (*)(int, unsigned*);
using PFNGLBINDBUFFERPROC = void (*)(unsigned, unsigned);
using PFNGLBUFFERDATAPROC = void (*)(unsigned, ptrdiff_t, const void*, unsigned);
using PFNGLCREATESHADERPROC = unsigned (*)(unsigned);
using PFNGLSHADERSOURCEPROC = void (*)(unsigned, int, const char* const*, const int*);
using PFNGLCOMPILESHADERPROC = void (*)(unsigned);
using PFNGLCREATEPROGRAMPROC = unsigned (*)();
using PFNGLATTACHSHADERPROC = void (*)(unsigned, unsigned);
using PFNGLLINKPROGRAMPROC = void (*)(unsigned);
using PFNGLUSEPROGRAMPROC = void (*)(unsigned);
using PFNGLGETUNIFORMLOCATIONPROC = int (*)(unsigned, const char*);
using PFNGLUNIFORM4FPROC = void (*)(int, float, float, float, float);
using PFNGLUNIFORM2FPROC = void (*)(int, float, float);
using PFNGLGENVERTEXARRAYSPROC = void (*)(int, unsigned*);
using PFNGLBINDVERTEXARRAYPROC = void (*)(unsigned);
using PFNGLENABLEVERTEXATTRIBARRAYPROC = void (*)(unsigned);
using PFNGLVERTEXATTRIBPOINTERPROC = void (*)(unsigned, int, unsigned, unsigned char, int, const void*);
using PFNGLDRAWARRAYSPROC = void (*)(unsigned, int, int);
using PFNGLDELETEBUFFERSPROC = void (*)(int, const unsigned*);
using PFNGLDELETEVERTEXARRAYSPROC = void (*)(int, const unsigned*);
using PFNGLDELETESHADERPROC = void (*)(unsigned);
using PFNGLDELETEPROGRAMPROC = void (*)(unsigned);
using PFNGLGETSHADERIVPROC = void (*)(unsigned, unsigned, int*);
using PFNGLGETPROGRAMIVPROC = void (*)(unsigned, unsigned, int*);

constexpr unsigned GL_ARRAY_BUFFER = 0x8892;
constexpr unsigned GL_STATIC_DRAW = 0x88E4;
constexpr unsigned GL_FRAGMENT_SHADER = 0x8B30;
constexpr unsigned GL_VERTEX_SHADER = 0x8B31;
constexpr unsigned GL_COMPILE_STATUS = 0x8B81;
constexpr unsigned GL_LINK_STATUS = 0x8B82;
constexpr unsigned GL_TRIANGLES = 0x0004;
constexpr unsigned GL_FLOAT = 0x1406;
constexpr unsigned GL_FALSE_ = 0;

template <class T>
T load(const char* name) {
  return reinterpret_cast<T>(SDL_GL_GetProcAddress(name));
}
}

struct OpenGLRenderer::Impl {
  SDL_Window* window = nullptr;
  SDL_GLContext ctx = nullptr;
  int w = 0, h = 0;
  unsigned vao = 0, vbo = 0, prog = 0;
  int u_color = -1, u_rect = -1, u_viewport = -1;
  bool pipeline = false;
  std::vector<Rect> clips;
};

static const char* kVert = R"(#version 330 core
uniform vec4 uRect; // x,y,w,h logical top-left
uniform vec2 uViewport;
void main() {
  vec2 corners[6] = vec2[](
    vec2(0,0), vec2(1,0), vec2(1,1),
    vec2(0,0), vec2(1,1), vec2(0,1));
  vec2 p = corners[gl_VertexID];
  vec2 px = vec2(uRect.x + p.x * uRect.z, uRect.y + p.y * uRect.w);
  vec2 ndc = vec2(px.x / uViewport.x * 2.0 - 1.0,
                  1.0 - px.y / uViewport.y * 2.0);
  gl_Position = vec4(ndc, 0.0, 1.0);
}
)";

static const char* kFrag = R"(#version 330 core
uniform vec4 uColor;
out vec4 frag;
void main() { frag = uColor; }
)";

OpenGLRenderer::OpenGLRenderer(void* sdl_window) : impl_(std::make_unique<Impl>()) {
  impl_->window = static_cast<SDL_Window*>(sdl_window);
  impl_->ctx = SDL_GL_CreateContext(impl_->window);
  if (!impl_->ctx) throw std::runtime_error(SDL_GetError());
  if (!SDL_GL_MakeCurrent(impl_->window, impl_->ctx)) {
    SDL_GL_DestroyContext(impl_->ctx);
    impl_->ctx = nullptr;
    throw std::runtime_error(SDL_GetError());
  }
  SDL_GetWindowSizeInPixels(impl_->window, &impl_->w, &impl_->h);
  glViewport(0, 0, impl_->w, impl_->h);
}

OpenGLRenderer::~OpenGLRenderer() {
  if (impl_ && impl_->ctx) {
    SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
    if (impl_->pipeline) {
      auto delProg = load<PFNGLDELETEPROGRAMPROC>("glDeleteProgram");
      auto delBuf = load<PFNGLDELETEBUFFERSPROC>("glDeleteBuffers");
      auto delVao = load<PFNGLDELETEVERTEXARRAYSPROC>("glDeleteVertexArrays");
      if (delProg && impl_->prog) delProg(impl_->prog);
      if (delBuf && impl_->vbo) delBuf(1, &impl_->vbo);
      if (delVao && impl_->vao) delVao(1, &impl_->vao);
    }
    SDL_GL_DestroyContext(impl_->ctx);
    impl_->ctx = nullptr;
  }
}

void OpenGLRenderer::ensure_quad_pipeline() {
  if (impl_->pipeline) return;
  auto genVao = load<PFNGLGENVERTEXARRAYSPROC>("glGenVertexArrays");
  auto bindVao = load<PFNGLBINDVERTEXARRAYPROC>("glBindVertexArray");
  auto genBuf = load<PFNGLGENBUFFERSPROC>("glGenBuffers");
  auto bindBuf = load<PFNGLBINDBUFFERPROC>("glBindBuffer");
  auto bufData = load<PFNGLBUFFERDATAPROC>("glBufferData");
  auto createShader = load<PFNGLCREATESHADERPROC>("glCreateShader");
  auto shaderSource = load<PFNGLSHADERSOURCEPROC>("glShaderSource");
  auto compile = load<PFNGLCOMPILESHADERPROC>("glCompileShader");
  auto createProg = load<PFNGLCREATEPROGRAMPROC>("glCreateProgram");
  auto attach = load<PFNGLATTACHSHADERPROC>("glAttachShader");
  auto link = load<PFNGLLINKPROGRAMPROC>("glLinkProgram");
  auto use = load<PFNGLUSEPROGRAMPROC>("glUseProgram");
  auto getLoc = load<PFNGLGETUNIFORMLOCATIONPROC>("glGetUniformLocation");
  auto delShader = load<PFNGLDELETESHADERPROC>("glDeleteShader");
  auto getShaderiv = load<PFNGLGETSHADERIVPROC>("glGetShaderiv");
  auto getProgramiv = load<PFNGLGETPROGRAMIVPROC>("glGetProgramiv");
  if (!genVao || !createShader || !createProg) return;

  auto make = [&](unsigned type, const char* src) {
    unsigned s = createShader(type);
    shaderSource(s, 1, &src, nullptr);
    compile(s);
    int ok = 0; getShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) throw std::runtime_error("shader compile failed");
    return s;
  };
  unsigned vs = make(GL_VERTEX_SHADER, kVert);
  unsigned fs = make(GL_FRAGMENT_SHADER, kFrag);
  impl_->prog = createProg();
  attach(impl_->prog, vs); attach(impl_->prog, fs); link(impl_->prog);
  int ok = 0; getProgramiv(impl_->prog, GL_LINK_STATUS, &ok);
  if (!ok) throw std::runtime_error("shader link failed");
  delShader(vs); delShader(fs);
  genVao(1, &impl_->vao);
  bindVao(impl_->vao);
  genBuf(1, &impl_->vbo);
  bindBuf(GL_ARRAY_BUFFER, impl_->vbo);
  float dummy = 0.f;
  bufData(GL_ARRAY_BUFFER, sizeof(dummy), &dummy, GL_STATIC_DRAW);
  impl_->u_color = getLoc(impl_->prog, "uColor");
  impl_->u_rect = getLoc(impl_->prog, "uRect");
  impl_->u_viewport = getLoc(impl_->prog, "uViewport");
  use(0);
  impl_->pipeline = true;
}

void OpenGLRenderer::clear(Color c) {
  if (!impl_ || !impl_->ctx) return;
  SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
  glViewport(0, 0, impl_->w, impl_->h);
  glClearColor(c.r / 255.f, c.g / 255.f, c.b / 255.f, c.a / 255.f);
  glClear(GL_COLOR_BUFFER_BIT);
}

void OpenGLRenderer::fill_rect(Rect r, Color c, float /*radius*/) {
  if (!impl_ || !impl_->ctx) return;
  if (!(r.w > 0 && r.h > 0)) return;
  if (!std::isfinite(r.x) || !std::isfinite(r.y) || !std::isfinite(r.w) || !std::isfinite(r.h)) return;
  if (r.w > kMaxLayoutDim || r.h > kMaxLayoutDim) return;
  SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
  ensure_quad_pipeline();
  if (!impl_->pipeline) return;
  auto use = load<PFNGLUSEPROGRAMPROC>("glUseProgram");
  auto bindVao = load<PFNGLBINDVERTEXARRAYPROC>("glBindVertexArray");
  auto uni4 = load<PFNGLUNIFORM4FPROC>("glUniform4f");
  auto uni2 = load<PFNGLUNIFORM2FPROC>("glUniform2f");
  auto draw = load<PFNGLDRAWARRAYSPROC>("glDrawArrays");
  use(impl_->prog);
  bindVao(impl_->vao);
  uni4(impl_->u_rect, r.x, r.y, r.w, r.h);
  uni2(impl_->u_viewport, float(impl_->w), float(impl_->h));
  uni4(impl_->u_color, c.r / 255.f, c.g / 255.f, c.b / 255.f, c.a / 255.f);
  draw(GL_TRIANGLES, 0, 6);
  use(0);
}

void OpenGLRenderer::stroke_rect(Rect, Color, float, float) {}
void OpenGLRenderer::clip_push(Rect r) { impl_->clips.push_back(r); }
void OpenGLRenderer::clip_pop() { if (!impl_->clips.empty()) impl_->clips.pop_back(); }

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
