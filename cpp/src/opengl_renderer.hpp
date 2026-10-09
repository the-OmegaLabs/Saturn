#pragma once
#include "saturn/renderer.hpp"
#include <memory>
namespace saturn {
class OpenGLRenderer final : public Renderer {
public:
  explicit OpenGLRenderer(void* sdl_window);
  ~OpenGLRenderer() override;
  void clear(Color c) override;
  void fill_rect(Rect r, Color c, float radius) override;
  void fill_rects(const Rect* rects, std::size_t count, Color c) override;
  void stroke_rect(Rect r, Color c, float width, float radius) override;
  void clip_push(Rect r) override;
  void clip_pop() override;
  void flip() override;
  void on_resize(int w, int h) override;
  void* create_texture_rgba8(int w, int h, const std::uint8_t* rgba) override;
  void destroy_texture(void* tex) override;
  void draw_textured_quads(void* tex, const TexturedQuad* quads, std::size_t count, Color tint) override;
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
  void ensure_quad_pipeline();
  void ensure_tex_pipeline();
  void apply_scissor();
};
}
