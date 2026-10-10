#include "saturn/control.hpp"
#include "saturn/colors.hpp"
#include "saturn/font.hpp"
#include "saturn/page.hpp"
#include "saturn/window.hpp"
#include "saturn/renderer.hpp"
#include "saturn/limits.hpp"
#include "stb_image_write.h"
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
struct Scene {
  saturn::Page page;
  saturn::FilledButton* button;
  saturn::Checkbox* checkbox;
  saturn::Switch* toggle;
  saturn::Slider* slider;
  saturn::TextField* field;
  saturn::Dropdown* menu;
  saturn::ListView* list;
  Scene() {
    using namespace saturn;
    auto b = std::make_unique<FilledButton>("Filled",[]{}); button = b.get(); page.add(std::move(b));
    auto c = std::make_unique<Checkbox>("agree"); checkbox = c.get(); page.add(std::move(c));
    auto t = std::make_unique<Switch>(); toggle = t.get(); page.add(std::move(t));
    auto s = std::make_unique<Slider>(0.f,100.f,10); slider = s.get(); page.add(std::move(s));
    auto f = std::make_unique<TextField>("Name"); field = f.get(); page.add(std::move(f));
    auto m = std::make_unique<Dropdown>("dropdown...",
        std::vector<DropdownOption>{{"a","Alpha"},{"b","Beta"},{"g","Gamma"}});
    menu = m.get(); page.add(std::move(m));
    ControlOptions opt; opt.width = 180.f; opt.height = 180.f;
    auto l = std::make_unique<ListView>(4.f,opt); list = l.get();
    for (int i = 0; i < 30; ++i) {
      auto row = std::make_unique<Container>();
      row->set_padding(8); row->set_corner_radius(6);
      row->set_bgcolor(i%2 ? colors::kSurfaceContainerLow : colors::kSurfaceContainer);
      row->add(std::make_unique<Text>("list item "+std::to_string(i),colors::kOnSurface,13.f));
      l->add(std::move(row));
    }
    page.add(std::move(l));
    place();
  }
  void place() {
    page.layout(640,480);
    button->set_rect({24,24,120,40});
    checkbox->set_rect({24,100,100,40});
    toggle->set_rect({200,100,52,40});
    slider->set_rect({24,164,300,48});
    field->set_rect({24,244,300,56});
    menu->set_rect({360,244,180,56});
    list->set_rect({360,24,180,180}); list->layout();
  }
  void start() {
    page.tick(10);
    button->on_hover(true); button->on_pointer({30,44,true});
    checkbox->on_pointer({33,120,true}); checkbox->on_pointer({33,120,false,true});
    toggle->set_value(true);
    slider->on_pointer({174,188,true});
    field->on_hover(true); field->on_focus(true);
    list->on_scroll({380,40,-2});
    menu->set_open(true);
  }
  void release() {
    button->on_pointer({30,44,false,true});
    checkbox->set_value(false);
    toggle->set_value(false);
    slider->on_pointer({174,188,false,true});
    field->on_focus(false); field->on_hover(false);
    menu->set_open(false);
  }
};
void save(saturn::Renderer& r,const std::filesystem::path& path) {
  std::vector<std::uint8_t> pixels;
  int w = 0,h = 0;
  if (!r.read_pixels_rgba(&pixels,&w,&h)) throw std::runtime_error("readback failed");
  if (std::size_t(w)*std::size_t(h) > saturn::kMaxScreenshotPixels)
    throw std::runtime_error("capture too large");
  if (!stbi_write_png(path.string().c_str(),w,h,4,pixels.data(),w*4))
    throw std::runtime_error("PNG write failed");
}
}
int main(int argc,char** argv) {
  try {
    if (argc != 2) throw std::invalid_argument("usage: saturn_visual_frames output_directory");
    const std::filesystem::path out(argv[1]);
    if (out.string().size() > saturn::kMaxPathBytes) throw std::invalid_argument("path too long");
    std::filesystem::create_directories(out);
    saturn::Window window("Saturn animation verification",640,480);
    saturn::set_default_font(saturn::Font::load_default());
    auto& renderer = window.renderer();
    {
      Scene scene;
      scene.start();
      for (int ms : {0,15,50,75,100,150,200,250,300,330,375,400,449,500,600,850}) {
        scene.page.tick(10+ms/1000.0);
        if (ms == 300) scene.release();
        scene.place();
        renderer.clear(saturn::colors::kSurface);
        scene.page.paint(renderer);
        save(renderer,out/("controls-"+std::to_string(ms)+".png"));
      }
    }
    for (const std::string kind : {"dialog","snack"}) {
      saturn::Page page; page.tick(10);
      std::unique_ptr<saturn::DialogControl> overlay;
      if (kind == "dialog") {
        std::vector<std::unique_ptr<saturn::Control>> actions;
        actions.push_back(std::make_unique<saturn::TextButton>("Cancel",[]{}));
        actions.push_back(std::make_unique<saturn::FilledButton>("Delete",[]{}));
        overlay = std::make_unique<saturn::AlertDialog>("Confirm","Delete this item permanently?",std::move(actions));
      } else overlay = std::make_unique<saturn::SnackBar>("Saved!","Undo");
      auto* raw = overlay.get();
      page.show_dialog(std::move(overlay)); page.layout(640,480);
      for (int ms : {0,30,75,150,225,300,330,375,450,500}) {
        page.tick(10+ms/1000.0);
        if (ms == 300) { page.pop_dialog(raw); page.tick(10.3); }
        if (page.layout_dirty()) page.layout(640,480);
        renderer.clear(saturn::colors::kSurface); page.paint(renderer);
        save(renderer,out/(kind+"-"+std::to_string(ms)+".png"));
      }
    }
    std::cout << "captured 36 deterministic OpenGL frames\n";
    return 0;
  } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
