#include "opengl_renderer.hpp"
#include "saturn/limits.hpp"
#include <SDL3/SDL.h>
#include <stdexcept>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdint>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif
#include <GL/gl.h>

namespace saturn {
namespace {
using PFNGLGENBUFFERSPROC = void (*)(int, unsigned*);
using PFNGLBINDBUFFERPROC = void (*)(unsigned, unsigned);
using PFNGLBUFFERDATAPROC = void (*)(unsigned, ptrdiff_t, const void*, unsigned);
using PFNGLBUFFERSUBDATAPROC = void (*)(unsigned, ptrdiff_t, ptrdiff_t, const void*);
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
using PFNGLUNIFORM1IPROC = void (*)(int, int);
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
using PFNGLENABLEPROC = void (*)(unsigned);
using PFNGLDISABLEPROC = void (*)(unsigned);
using PFNGLSCISSORPROC = void (*)(int, int, int, int);
using PFNGLGENTEXTURESPROC = void (*)(int, unsigned*);
using PFNGLDELETETEXTURESPROC = void (*)(int, const unsigned*);
using PFNGLBINDTEXTUREPROC = void (*)(unsigned, unsigned);
using PFNGLTEXIMAGE2DPROC = void (*)(unsigned, int, int, int, int, int, unsigned, unsigned, const void*);
using PFNGLTEXPARAMETERIPROC = void (*)(unsigned, unsigned, int);
using PFNGLACTIVETEXTUREPROC = void (*)(unsigned);
using PFNGLBLENDFUNCPROC = void (*)(unsigned, unsigned);

constexpr unsigned kArrBuf = 0x8892;
constexpr unsigned kDynamicDraw = 0x88E8;
constexpr unsigned kFragShader = 0x8B30;
constexpr unsigned kVertShader = 0x8B31;
constexpr unsigned kCompileStatus = 0x8B81;
constexpr unsigned kLinkStatus = 0x8B82;
constexpr unsigned kScissorTest = 0x0C11;
constexpr unsigned kFloat = 0x1406;
constexpr unsigned kFalse = 0;
constexpr unsigned kTexture2D = 0x0DE1;
constexpr unsigned kRGBA = 0x1908;
constexpr unsigned kUnsignedByte = 0x1401;
constexpr unsigned kNearest = 0x2600;
constexpr unsigned kClampToEdge = 0x812F;
constexpr unsigned kTexture0 = 0x84C0;
constexpr unsigned kTexMinFilter = 0x2801;
constexpr unsigned kTexMagFilter = 0x2800;
constexpr unsigned kTexWrapS = 0x2802;
constexpr unsigned kTexWrapT = 0x2803;
constexpr unsigned kBlend = 0x0BE2;
constexpr unsigned kSrcAlpha = 0x0302;
constexpr unsigned kOneMinusSrcAlpha = 0x0303;
constexpr int kRgba8 = 0x8058; // GL_RGBA8

struct GlApi {
  PFNGLGENBUFFERSPROC genBuffers = nullptr;
  PFNGLBINDBUFFERPROC bindBuffer = nullptr;
  PFNGLBUFFERDATAPROC bufferData = nullptr;
  PFNGLBUFFERSUBDATAPROC bufferSubData = nullptr;
  PFNGLCREATESHADERPROC createShader = nullptr;
  PFNGLSHADERSOURCEPROC shaderSource = nullptr;
  PFNGLCOMPILESHADERPROC compileShader = nullptr;
  PFNGLCREATEPROGRAMPROC createProgram = nullptr;
  PFNGLATTACHSHADERPROC attachShader = nullptr;
  PFNGLLINKPROGRAMPROC linkProgram = nullptr;
  PFNGLUSEPROGRAMPROC useProgram = nullptr;
  PFNGLGETUNIFORMLOCATIONPROC getUniformLocation = nullptr;
  PFNGLUNIFORM4FPROC uniform4f = nullptr;
  PFNGLUNIFORM2FPROC uniform2f = nullptr;
  PFNGLUNIFORM1IPROC uniform1i = nullptr;
  PFNGLGENVERTEXARRAYSPROC genVertexArrays = nullptr;
  PFNGLBINDVERTEXARRAYPROC bindVertexArray = nullptr;
  PFNGLENABLEVERTEXATTRIBARRAYPROC enableVertexAttribArray = nullptr;
  PFNGLVERTEXATTRIBPOINTERPROC vertexAttribPointer = nullptr;
  PFNGLDRAWARRAYSPROC drawArrays = nullptr;
  PFNGLDELETEBUFFERSPROC deleteBuffers = nullptr;
  PFNGLDELETEVERTEXARRAYSPROC deleteVertexArrays = nullptr;
  PFNGLDELETESHADERPROC deleteShader = nullptr;
  PFNGLDELETEPROGRAMPROC deleteProgram = nullptr;
  PFNGLGETSHADERIVPROC getShaderiv = nullptr;
  PFNGLGETPROGRAMIVPROC getProgramiv = nullptr;
  PFNGLENABLEPROC enable = nullptr;
  PFNGLDISABLEPROC disable = nullptr;
  PFNGLSCISSORPROC scissor = nullptr;
  PFNGLGENTEXTURESPROC genTextures = nullptr;
  PFNGLDELETETEXTURESPROC deleteTextures = nullptr;
  PFNGLBINDTEXTUREPROC bindTexture = nullptr;
  PFNGLTEXIMAGE2DPROC texImage2D = nullptr;
  PFNGLTEXPARAMETERIPROC texParameteri = nullptr;
  PFNGLACTIVETEXTUREPROC activeTexture = nullptr;
  PFNGLBLENDFUNCPROC blendFunc = nullptr;
  bool loaded = false;

  void load_all() {
    if (loaded) return;
    auto L = [](const char* n) { return SDL_GL_GetProcAddress(n); };
    genBuffers = reinterpret_cast<PFNGLGENBUFFERSPROC>(L("glGenBuffers"));
    bindBuffer = reinterpret_cast<PFNGLBINDBUFFERPROC>(L("glBindBuffer"));
    bufferData = reinterpret_cast<PFNGLBUFFERDATAPROC>(L("glBufferData"));
    bufferSubData = reinterpret_cast<PFNGLBUFFERSUBDATAPROC>(L("glBufferSubData"));
    createShader = reinterpret_cast<PFNGLCREATESHADERPROC>(L("glCreateShader"));
    shaderSource = reinterpret_cast<PFNGLSHADERSOURCEPROC>(L("glShaderSource"));
    compileShader = reinterpret_cast<PFNGLCOMPILESHADERPROC>(L("glCompileShader"));
    createProgram = reinterpret_cast<PFNGLCREATEPROGRAMPROC>(L("glCreateProgram"));
    attachShader = reinterpret_cast<PFNGLATTACHSHADERPROC>(L("glAttachShader"));
    linkProgram = reinterpret_cast<PFNGLLINKPROGRAMPROC>(L("glLinkProgram"));
    useProgram = reinterpret_cast<PFNGLUSEPROGRAMPROC>(L("glUseProgram"));
    getUniformLocation = reinterpret_cast<PFNGLGETUNIFORMLOCATIONPROC>(L("glGetUniformLocation"));
    uniform4f = reinterpret_cast<PFNGLUNIFORM4FPROC>(L("glUniform4f"));
    uniform2f = reinterpret_cast<PFNGLUNIFORM2FPROC>(L("glUniform2f"));
    uniform1i = reinterpret_cast<PFNGLUNIFORM1IPROC>(L("glUniform1i"));
    genVertexArrays = reinterpret_cast<PFNGLGENVERTEXARRAYSPROC>(L("glGenVertexArrays"));
    bindVertexArray = reinterpret_cast<PFNGLBINDVERTEXARRAYPROC>(L("glBindVertexArray"));
    enableVertexAttribArray = reinterpret_cast<PFNGLENABLEVERTEXATTRIBARRAYPROC>(L("glEnableVertexAttribArray"));
    vertexAttribPointer = reinterpret_cast<PFNGLVERTEXATTRIBPOINTERPROC>(L("glVertexAttribPointer"));
    drawArrays = reinterpret_cast<PFNGLDRAWARRAYSPROC>(L("glDrawArrays"));
    deleteBuffers = reinterpret_cast<PFNGLDELETEBUFFERSPROC>(L("glDeleteBuffers"));
    deleteVertexArrays = reinterpret_cast<PFNGLDELETEVERTEXARRAYSPROC>(L("glDeleteVertexArrays"));
    deleteShader = reinterpret_cast<PFNGLDELETESHADERPROC>(L("glDeleteShader"));
    deleteProgram = reinterpret_cast<PFNGLDELETEPROGRAMPROC>(L("glDeleteProgram"));
    getShaderiv = reinterpret_cast<PFNGLGETSHADERIVPROC>(L("glGetShaderiv"));
    getProgramiv = reinterpret_cast<PFNGLGETPROGRAMIVPROC>(L("glGetProgramiv"));
    enable = reinterpret_cast<PFNGLENABLEPROC>(L("glEnable"));
    disable = reinterpret_cast<PFNGLDISABLEPROC>(L("glDisable"));
    scissor = reinterpret_cast<PFNGLSCISSORPROC>(L("glScissor"));
    genTextures = reinterpret_cast<PFNGLGENTEXTURESPROC>(L("glGenTextures"));
    deleteTextures = reinterpret_cast<PFNGLDELETETEXTURESPROC>(L("glDeleteTextures"));
    bindTexture = reinterpret_cast<PFNGLBINDTEXTUREPROC>(L("glBindTexture"));
    texImage2D = reinterpret_cast<PFNGLTEXIMAGE2DPROC>(L("glTexImage2D"));
    texParameteri = reinterpret_cast<PFNGLTEXPARAMETERIPROC>(L("glTexParameteri"));
    activeTexture = reinterpret_cast<PFNGLACTIVETEXTUREPROC>(L("glActiveTexture"));
    blendFunc = reinterpret_cast<PFNGLBLENDFUNCPROC>(L("glBlendFunc"));
    loaded = genVertexArrays && createShader && createProgram && drawArrays &&
             enableVertexAttribArray && vertexAttribPointer &&
             enable && disable && scissor &&
             genTextures && bindTexture && texImage2D && texParameteri;
  }
};

}  // namespace

struct OpenGLRenderer::Impl {
  struct GpuTexture {
    unsigned id = 0;
    int w = 0;
    int h = 0;
  };
  SDL_Window* window = nullptr;
  SDL_GLContext ctx = nullptr;
  int w = 0, h = 0;
  unsigned vao = 0, vbo = 0, prog = 0;
  int u_color = -1, u_viewport = -1;
  bool pipeline = false;
  std::size_t vbo_capacity = 0; // floats
  unsigned tex_vao = 0, tex_vbo = 0, tex_prog = 0;
  int u_tex_viewport = -1, u_tex_size = -1, u_tint = -1, u_sampler = -1;
  bool tex_pipeline = false;
  std::size_t tex_vbo_capacity = 0; // floats
  std::vector<Rect> clips;
  std::vector<float> scratch; // solid: x,y; textured: x,y,u,v
  std::vector<GpuTexture*> textures;
  GlApi gl;
};

static const char* kVert = R"(#version 330 core
layout(location = 0) in vec2 aPos;
uniform vec2 uViewport;
void main() {
  vec2 ndc = vec2(aPos.x / uViewport.x * 2.0 - 1.0,
                  1.0 - aPos.y / uViewport.y * 2.0);
  gl_Position = vec4(ndc, 0.0, 1.0);
}
)";

static const char* kFrag = R"(#version 330 core
uniform vec4 uColor;
out vec4 frag;
void main() { frag = uColor; }
)";

static const char* kTexVert = R"(#version 330 core
layout(location = 0) in vec2 aPos;
layout(location = 1) in vec2 aUV;
uniform vec2 uViewport;
uniform vec2 uTexSize;
out vec2 vUV;
void main() {
  vec2 ndc = vec2(aPos.x / uViewport.x * 2.0 - 1.0,
                  1.0 - aPos.y / uViewport.y * 2.0);
  gl_Position = vec4(ndc, 0.0, 1.0);
  vUV = aUV / uTexSize;
}
)";

static const char* kTexFrag = R"(#version 330 core
uniform sampler2D uTex;
uniform vec4 uTint;
in vec2 vUV;
out vec4 frag;
void main() { frag = texture(uTex, vUV) * uTint; }
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
  impl_->gl.load_all();
}

OpenGLRenderer::~OpenGLRenderer() {
  if (impl_ && impl_->ctx) {
    SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
    auto& g = impl_->gl;
    for (Impl::GpuTexture* t : impl_->textures) {
      if (t && t->id && g.deleteTextures) g.deleteTextures(1, &t->id);
      delete t;
    }
    impl_->textures.clear();
    if (impl_->tex_pipeline) {
      if (g.deleteProgram && impl_->tex_prog) g.deleteProgram(impl_->tex_prog);
      if (g.deleteBuffers && impl_->tex_vbo) g.deleteBuffers(1, &impl_->tex_vbo);
      if (g.deleteVertexArrays && impl_->tex_vao) g.deleteVertexArrays(1, &impl_->tex_vao);
    }
    if (impl_->pipeline) {
      if (g.deleteProgram && impl_->prog) g.deleteProgram(impl_->prog);
      if (g.deleteBuffers && impl_->vbo) g.deleteBuffers(1, &impl_->vbo);
      if (g.deleteVertexArrays && impl_->vao) g.deleteVertexArrays(1, &impl_->vao);
    }
    SDL_GL_DestroyContext(impl_->ctx);
    impl_->ctx = nullptr;
  }
}

void OpenGLRenderer::ensure_quad_pipeline() {
  if (impl_->pipeline) return;
  auto& g = impl_->gl;
  g.load_all();
  if (!g.loaded) return;

  unsigned vs = 0, fs = 0;
  auto cleanup_shaders = [&]() {
    if (vs && g.deleteShader) g.deleteShader(vs);
    if (fs && g.deleteShader) g.deleteShader(fs);
  };
  try {
    auto make = [&](unsigned type, const char* src) {
      unsigned s = g.createShader(type);
      g.shaderSource(s, 1, &src, nullptr);
      g.compileShader(s);
      int ok = 0; g.getShaderiv(s, kCompileStatus, &ok);
      if (!ok) {
        if (g.deleteShader) g.deleteShader(s);
        throw std::runtime_error("shader compile failed");
      }
      return s;
    };
    vs = make(kVertShader, kVert);
    fs = make(kFragShader, kFrag);
    impl_->prog = g.createProgram();
    g.attachShader(impl_->prog, vs);
    g.attachShader(impl_->prog, fs);
    g.linkProgram(impl_->prog);
    int ok = 0; g.getProgramiv(impl_->prog, kLinkStatus, &ok);
    if (!ok) {
      if (g.deleteProgram) { g.deleteProgram(impl_->prog); impl_->prog = 0; }
      cleanup_shaders();
      throw std::runtime_error("shader link failed");
    }
    cleanup_shaders();
    vs = fs = 0;
    g.genVertexArrays(1, &impl_->vao);
    g.bindVertexArray(impl_->vao);
    g.genBuffers(1, &impl_->vbo);
    g.bindBuffer(kArrBuf, impl_->vbo);
    impl_->vbo_capacity = 64;
    g.bufferData(kArrBuf, ptrdiff_t(impl_->vbo_capacity * sizeof(float)), nullptr, kDynamicDraw);
    g.enableVertexAttribArray(0);
    g.vertexAttribPointer(0, 2, kFloat, kFalse, 0, nullptr);
    impl_->u_color = g.getUniformLocation(impl_->prog, "uColor");
    impl_->u_viewport = g.getUniformLocation(impl_->prog, "uViewport");
    g.useProgram(0);
    impl_->pipeline = true;
  } catch (...) {
    cleanup_shaders();
    if (impl_->prog && g.deleteProgram) { g.deleteProgram(impl_->prog); impl_->prog = 0; }
    if (impl_->vbo && g.deleteBuffers) { g.deleteBuffers(1, &impl_->vbo); impl_->vbo = 0; }
    if (impl_->vao && g.deleteVertexArrays) { g.deleteVertexArrays(1, &impl_->vao); impl_->vao = 0; }
    throw;
  }
}

void OpenGLRenderer::ensure_tex_pipeline() {
  if (impl_->tex_pipeline) return;
  auto& g = impl_->gl;
  g.load_all();
  if (!g.loaded) return;

  unsigned vs = 0, fs = 0;
  auto cleanup_shaders = [&]() {
    if (vs && g.deleteShader) g.deleteShader(vs);
    if (fs && g.deleteShader) g.deleteShader(fs);
  };
  try {
    auto make = [&](unsigned type, const char* src) {
      unsigned s = g.createShader(type);
      g.shaderSource(s, 1, &src, nullptr);
      g.compileShader(s);
      int ok = 0; g.getShaderiv(s, kCompileStatus, &ok);
      if (!ok) {
        if (g.deleteShader) g.deleteShader(s);
        throw std::runtime_error("tex shader compile failed");
      }
      return s;
    };
    vs = make(kVertShader, kTexVert);
    fs = make(kFragShader, kTexFrag);
    impl_->tex_prog = g.createProgram();
    g.attachShader(impl_->tex_prog, vs);
    g.attachShader(impl_->tex_prog, fs);
    g.linkProgram(impl_->tex_prog);
    int ok = 0; g.getProgramiv(impl_->tex_prog, kLinkStatus, &ok);
    if (!ok) {
      if (g.deleteProgram) { g.deleteProgram(impl_->tex_prog); impl_->tex_prog = 0; }
      cleanup_shaders();
      throw std::runtime_error("tex shader link failed");
    }
    cleanup_shaders();
    vs = fs = 0;
    g.genVertexArrays(1, &impl_->tex_vao);
    g.bindVertexArray(impl_->tex_vao);
    g.genBuffers(1, &impl_->tex_vbo);
    g.bindBuffer(kArrBuf, impl_->tex_vbo);
    impl_->tex_vbo_capacity = 64;
    g.bufferData(kArrBuf, ptrdiff_t(impl_->tex_vbo_capacity * sizeof(float)), nullptr, kDynamicDraw);
    const int stride = int(4 * sizeof(float));
    g.enableVertexAttribArray(0);
    g.vertexAttribPointer(0, 2, kFloat, kFalse, stride, nullptr);
    g.enableVertexAttribArray(1);
    g.vertexAttribPointer(1, 2, kFloat, kFalse, stride, reinterpret_cast<const void*>(sizeof(float) * 2));
    impl_->u_tex_viewport = g.getUniformLocation(impl_->tex_prog, "uViewport");
    impl_->u_tex_size = g.getUniformLocation(impl_->tex_prog, "uTexSize");
    impl_->u_tint = g.getUniformLocation(impl_->tex_prog, "uTint");
    impl_->u_sampler = g.getUniformLocation(impl_->tex_prog, "uTex");
    g.useProgram(0);
    impl_->tex_pipeline = true;
  } catch (...) {
    cleanup_shaders();
    if (impl_->tex_prog && g.deleteProgram) { g.deleteProgram(impl_->tex_prog); impl_->tex_prog = 0; }
    if (impl_->tex_vbo && g.deleteBuffers) { g.deleteBuffers(1, &impl_->tex_vbo); impl_->tex_vbo = 0; }
    if (impl_->tex_vao && g.deleteVertexArrays) { g.deleteVertexArrays(1, &impl_->tex_vao); impl_->tex_vao = 0; }
    throw;
  }
}

void OpenGLRenderer::apply_scissor() {
  auto& g = impl_->gl;
  if (impl_->clips.empty()) {
    if (g.disable) g.disable(kScissorTest);
    return;
  }
  Rect r = impl_->clips.front();
  for (std::size_t i = 1; i < impl_->clips.size(); ++i) {
    const Rect& c = impl_->clips[i];
    float x2 = (std::min)(r.x + r.w, c.x + c.w);
    float y2 = (std::min)(r.y + r.h, c.y + c.h);
    r.x = (std::max)(r.x, c.x);
    r.y = (std::max)(r.y, c.y);
    r.w = (std::max)(0.f, x2 - r.x);
    r.h = (std::max)(0.f, y2 - r.y);
  }
  int sx = int(std::floor(r.x));
  int sy = int(std::floor(impl_->h - (r.y + r.h)));
  int sw = int(std::ceil(r.w));
  int sh = int(std::ceil(r.h));
  if (sw <= 0 || sh <= 0) {
    g.enable(kScissorTest);
    g.scissor(0, 0, 0, 0);
    return;
  }
  g.enable(kScissorTest);
  g.scissor(sx, sy, sw, sh);
}

void OpenGLRenderer::clear(Color c) {
  if (!impl_ || !impl_->ctx) return;
  SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
  glViewport(0, 0, impl_->w, impl_->h);
  if (impl_->gl.disable) impl_->gl.disable(kScissorTest);
  glClearColor(c.r / 255.f, c.g / 255.f, c.b / 255.f, c.a / 255.f);
  glClear(GL_COLOR_BUFFER_BIT);
  apply_scissor();
}

static void append_rect(std::vector<float>& out, const Rect& r) {
  float x0 = r.x, y0 = r.y, x1 = r.x + r.w, y1 = r.y + r.h;
  out.insert(out.end(), {x0,y0, x1,y0, x1,y1, x0,y0, x1,y1, x0,y1});
}

static void append_textured(std::vector<float>& out, const Rect& dst, const Rect& uv) {
  float x0 = dst.x, y0 = dst.y, x1 = dst.x + dst.w, y1 = dst.y + dst.h;
  float u0 = uv.x, v0 = uv.y, u1 = uv.x + uv.w, v1 = uv.y + uv.h;
  out.insert(out.end(), {
    x0,y0,u0,v0, x1,y0,u1,v0, x1,y1,u1,v1,
    x0,y0,u0,v0, x1,y1,u1,v1, x0,y1,u0,v1});
}

void OpenGLRenderer::fill_rect(Rect r, Color c, float /*radius*/) {
  fill_rects(&r, 1, c);
}

void OpenGLRenderer::fill_rects(const Rect* rects, std::size_t count, Color c) {
  if (count > kMaxFillRects)
    throw std::runtime_error("fill_rects exceeds kMaxFillRects");
  if (!impl_ || !impl_->ctx || !rects || count == 0) return;
  SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
  ensure_quad_pipeline();
  if (!impl_->pipeline) return;

  impl_->scratch.clear();
  impl_->scratch.reserve(count * 12);
  for (std::size_t i = 0; i < count; ++i) {
    const Rect& r = rects[i];
    if (!(r.w > 0 && r.h > 0)) continue;
    if (!std::isfinite(r.x) || !std::isfinite(r.y) || !std::isfinite(r.w) || !std::isfinite(r.h)) continue;
    if (r.w > kMaxLayoutDim || r.h > kMaxLayoutDim) continue;
    append_rect(impl_->scratch, r);
  }
  if (impl_->scratch.empty()) return;

  auto& g = impl_->gl;
  apply_scissor();
  g.bindVertexArray(impl_->vao);
  g.bindBuffer(kArrBuf, impl_->vbo);
  const std::size_t floats = impl_->scratch.size();
  if (floats > impl_->vbo_capacity) {
    impl_->vbo_capacity = floats * 2;
    g.bufferData(kArrBuf, ptrdiff_t(impl_->vbo_capacity * sizeof(float)), nullptr, kDynamicDraw);
  }
  g.bufferSubData(kArrBuf, 0, ptrdiff_t(floats * sizeof(float)), impl_->scratch.data());
  g.useProgram(impl_->prog);
  g.uniform2f(impl_->u_viewport, float(impl_->w), float(impl_->h));
  g.uniform4f(impl_->u_color, c.r / 255.f, c.g / 255.f, c.b / 255.f, c.a / 255.f);
  g.drawArrays(GL_TRIANGLES, 0, int(floats / 2));
  g.useProgram(0);
}

void* OpenGLRenderer::create_texture_rgba8(int w, int h, const std::uint8_t* rgba) {
  if (!impl_ || !impl_->ctx || !rgba || w <= 0 || h <= 0) return nullptr;
  if (static_cast<std::size_t>(w) > kMaxLayoutDim || static_cast<std::size_t>(h) > kMaxLayoutDim)
    return nullptr;
  SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
  auto& g = impl_->gl;
  g.load_all();
  if (!g.genTextures || !g.bindTexture || !g.texImage2D || !g.texParameteri) return nullptr;
  unsigned id = 0;
  g.genTextures(1, &id);
  if (!id) return nullptr;
  g.bindTexture(kTexture2D, id);
  g.texParameteri(kTexture2D, kTexMinFilter, int(kNearest));
  g.texParameteri(kTexture2D, kTexMagFilter, int(kNearest));
  g.texParameteri(kTexture2D, kTexWrapS, int(kClampToEdge));
  g.texParameteri(kTexture2D, kTexWrapT, int(kClampToEdge));
  g.texImage2D(kTexture2D, 0, kRgba8, w, h, 0, kRGBA, kUnsignedByte, rgba);
  g.bindTexture(kTexture2D, 0);
  auto* rec = new Impl::GpuTexture{id, w, h};
  impl_->textures.push_back(rec);
  return rec;
}

void OpenGLRenderer::destroy_texture(void* tex) {
  if (!tex || !impl_) return;
  auto* rec = static_cast<Impl::GpuTexture*>(tex);
  auto& vec = impl_->textures;
  auto it = std::find(vec.begin(), vec.end(), rec);
  if (it == vec.end()) return;
  if (impl_->ctx) {
    SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
    if (rec->id && impl_->gl.deleteTextures) impl_->gl.deleteTextures(1, &rec->id);
  }
  vec.erase(it);
  delete rec;
}

void OpenGLRenderer::draw_textured_quads(void* tex, const TexturedQuad* quads, std::size_t count, Color tint) {
  if (count > kMaxFillRects)
    throw std::runtime_error("draw_textured_quads exceeds kMaxFillRects");
  if (!impl_ || !impl_->ctx || !tex || !quads || count == 0) return;
  auto* rec = static_cast<Impl::GpuTexture*>(tex);
  if (!rec->id || rec->w <= 0 || rec->h <= 0) return;
  SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
  ensure_tex_pipeline();
  if (!impl_->tex_pipeline) return;

  impl_->scratch.clear();
  impl_->scratch.reserve(count * 24);
  for (std::size_t i = 0; i < count; ++i) {
    const TexturedQuad& q = quads[i];
    if (!(q.dst.w > 0 && q.dst.h > 0)) continue;
    if (!std::isfinite(q.dst.x) || !std::isfinite(q.dst.y) ||
        !std::isfinite(q.dst.w) || !std::isfinite(q.dst.h)) continue;
    if (!std::isfinite(q.uv.x) || !std::isfinite(q.uv.y) ||
        !std::isfinite(q.uv.w) || !std::isfinite(q.uv.h)) continue;
    if (q.dst.w > kMaxLayoutDim || q.dst.h > kMaxLayoutDim) continue;
    append_textured(impl_->scratch, q.dst, q.uv);
  }
  if (impl_->scratch.empty()) return;

  auto& g = impl_->gl;
  apply_scissor();
  if (g.enable && g.blendFunc) {
    g.enable(kBlend);
    g.blendFunc(kSrcAlpha, kOneMinusSrcAlpha);
  }
  if (g.activeTexture) g.activeTexture(kTexture0);
  g.bindTexture(kTexture2D, rec->id);
  g.bindVertexArray(impl_->tex_vao);
  g.bindBuffer(kArrBuf, impl_->tex_vbo);
  const std::size_t floats = impl_->scratch.size();
  if (floats > impl_->tex_vbo_capacity) {
    impl_->tex_vbo_capacity = floats * 2;
    g.bufferData(kArrBuf, ptrdiff_t(impl_->tex_vbo_capacity * sizeof(float)), nullptr, kDynamicDraw);
  }
  g.bufferSubData(kArrBuf, 0, ptrdiff_t(floats * sizeof(float)), impl_->scratch.data());
  g.useProgram(impl_->tex_prog);
  g.uniform2f(impl_->u_tex_viewport, float(impl_->w), float(impl_->h));
  g.uniform2f(impl_->u_tex_size, float(rec->w), float(rec->h));
  g.uniform4f(impl_->u_tint, tint.r / 255.f, tint.g / 255.f, tint.b / 255.f, tint.a / 255.f);
  if (g.uniform1i && impl_->u_sampler >= 0) g.uniform1i(impl_->u_sampler, 0);
  g.drawArrays(GL_TRIANGLES, 0, int(floats / 4));
  g.useProgram(0);
  g.bindTexture(kTexture2D, 0);
}

void OpenGLRenderer::stroke_rect(Rect, Color, float, float) {}

void OpenGLRenderer::clip_push(Rect r) {
  if (impl_->clips.size() >= kMaxClipDepth)
    throw std::runtime_error("clip stack exceeds kMaxClipDepth");
  if (!std::isfinite(r.x) || !std::isfinite(r.y) || !std::isfinite(r.w) || !std::isfinite(r.h))
    throw std::invalid_argument("clip rect must be finite");
  impl_->clips.push_back(r);
  if (impl_->ctx) {
    SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
    apply_scissor();
  }
}

void OpenGLRenderer::clip_pop() {
  if (impl_->clips.empty()) return;
  impl_->clips.pop_back();
  if (impl_->ctx) {
    SDL_GL_MakeCurrent(impl_->window, impl_->ctx);
    apply_scissor();
  }
}

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
    apply_scissor();
  }
}
}
