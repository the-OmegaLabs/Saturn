#include "saturn/control.hpp"
#include "saturn/colors.hpp"
#include "saturn/renderer.hpp"
#include "saturn/window.hpp"
#include <SDL3/SDL.h>
#include "stb_image_write.h"
#include <chrono>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
void require(bool value,const char* message) {
  if (!value) throw std::runtime_error(message);
}
using GenQueries = void (*)(int,unsigned*);
using Query = void (*)(unsigned,unsigned);
using EndQuery = void (*)(unsigned);
using QueryResult = void (*)(unsigned,unsigned,unsigned long long*);
using DeleteQueries = void (*)(int,const unsigned*);
using Finish = void (*)();
using GetString = const unsigned char* (*)(unsigned);
}
int main(int argc,char** argv) {
  try {
    saturn::Window window("Saturn AA verification",640,480);
    auto& r = window.renderer();
    const auto finish = reinterpret_cast<Finish>(SDL_GL_GetProcAddress("glFinish"));
    const auto get_string = reinterpret_cast<GetString>(SDL_GL_GetProcAddress("glGetString"));
    require(finish && get_string,"GL core functions unavailable");
    std::cout << "GPU: " << get_string(0x1F01) << "\nGL: " << get_string(0x1F02) << '\n';

    r.clear({0,0,255,255});
    const std::uint8_t edge[] = {255,255,255,255, 0,0,0,0};
    void* texture = r.create_image_texture_rgba8(2,1,edge);
    require(texture != nullptr,"image upload");
    const saturn::TexturedQuad quad{{10,10,100,30},{0,0,2,1}};
    r.draw_textured_quads(texture,&quad,1,{255,255,255,255});
    std::vector<std::uint8_t> pixels; int w = 0,h = 0;
    require(r.read_pixels_rgba(&pixels,&w,&h),"readback");
    for (int x = 40; x < 80; ++x) {
      const auto p = (std::size_t(20)*w+x)*4;
      require(pixels[p+2] >= 250,"premultiplied filtering must not create a dark fringe");
    }
    const auto mid = (std::size_t(20)*w+60)*4;
    require(pixels[mid] > 80 && pixels[mid] < 170,"bilinear edge interpolation");
    r.destroy_texture(texture);

    r.clear({0,0,0,255});
    r.fill_rect({20.25f,20.25f,40,40},{255,255,255,255},20);
    r.draw_saturn_mark({80,20,52,42},{255,255,255,255});
    r.draw_saturn_mark({160,20,104,84},{255,255,255,255});
    r.draw_saturn_mark({300,20,208,168},{255,255,255,255});
    require(r.read_pixels_rgba(&pixels,&w,&h),"AA readback");
    int partial = 0,solid = 0;
    for (int y = 20; y < 62; ++y)
      for (int x = 80; x < 132; ++x) {
        const auto value = pixels[(std::size_t(y)*w+x)*4];
        if (value > 0 && value < 250) ++partial;
        if (value >= 250) ++solid;
      }
    require(partial > 20 && solid > 20,"mark must have smooth edges and a solid line core");
    for (int y = 80; y < 105; ++y)
      for (int x = 380; x < 420; ++x)
        require(pixels[(std::size_t(y)*w+x)*4] == 0,"mark interior must stay clean");
    bool rejected = false;
    try { r.draw_saturn_mark({NAN,0,52,42},{255,255,255,255}); }
    catch (const std::invalid_argument&) { rejected = true; }
    require(rejected,"non-finite mark rejected");

    if (argc > 1) {
      const std::filesystem::path output(argv[1]);
      std::filesystem::create_directories(output.parent_path());
      r.clear(saturn::colors::kSurface);
      {
        saturn::TextureImage bitmap("saturn-logo-transparent.png");
        bitmap.draw(r,{24,24,52,40},saturn::colors::kPrimary);
        r.draw_saturn_mark({120,24,52,42},saturn::colors::kPrimary);
        r.draw_saturn_mark({220,24,104,84},saturn::colors::kPrimary);
        r.draw_saturn_mark({350,24,208,168},saturn::colors::kPrimary);
        for (int i = 0; i < 4; ++i)
          r.draw_saturn_mark({24+float(i)*72,224,float(26+13*i),float(21+10.5*i)},
                            saturn::colors::kOnSurface);
        r.stroke_rect({24.25f,320.25f,120,64},saturn::colors::kPrimary,1,16);
        r.stroke_arc(240,350,30,0,4.2f,saturn::colors::kPrimary,2);
        require(r.read_pixels_rgba(&pixels,&w,&h),"sheet readback");
        require(stbi_write_png(output.string().c_str(),w,h,4,pixels.data(),w*4) != 0,"sheet write");
      }
    }
    auto gen = reinterpret_cast<GenQueries>(SDL_GL_GetProcAddress("glGenQueries"));
    auto begin = reinterpret_cast<Query>(SDL_GL_GetProcAddress("glBeginQuery"));
    auto end = reinterpret_cast<EndQuery>(SDL_GL_GetProcAddress("glEndQuery"));
    auto result = reinterpret_cast<QueryResult>(SDL_GL_GetProcAddress("glGetQueryObjectui64v"));
    auto destroy = reinterpret_cast<DeleteQueries>(SDL_GL_GetProcAddress("glDeleteQueries"));
    if (gen && begin && end && result && destroy) {
      unsigned query = 0; gen(1,&query);
      double cpu_ms = 0,gpu_ms = 0;
      for (int frame = 0; frame < 30; ++frame) {
        r.clear(saturn::colors::kSurface); finish();
        begin(0x88BF,query); // GL_TIME_ELAPSED
        const auto started = std::chrono::steady_clock::now();
        for (int i = 0; i < 100; ++i)
          r.draw_saturn_mark({float(i%10)*60,float(i/10)*44,52,42},saturn::colors::kPrimary);
        const auto submitted = std::chrono::steady_clock::now();
        end(0x88BF);
        unsigned long long ns = 0; result(query,0x8866,&ns);
        cpu_ms += std::chrono::duration<double,std::milli>(submitted-started).count();
        gpu_ms += double(ns)/1e6;
      }
      destroy(1,&query);
      std::cout << "100 marks/frame, 30 frames: CPU submission " << cpu_ms/30
                << " ms, GPU elapsed query " << gpu_ms/30 << " ms/frame\n";
    } else std::cout << "GPU timer unavailable; no timing claim\n";
    std::cout << "AA GPU tests passed\n";
    return 0;
  } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
