#include "saturn/control.hpp"
#include "saturn/colors.hpp"
#include "saturn/font.hpp"
#include "saturn/page.hpp"
#include "saturn/renderer.hpp"
#include "saturn/limits.hpp"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void require(bool condition, const char* message) {
  if (!condition) throw std::runtime_error(message);
}
struct Fill { saturn::Rect rect; saturn::Color color; float radius; };
struct State { float hover, press, x, y, radius; };
struct Effect { float x,y,alpha; };
class Recorder final : public saturn::Renderer {
public:
  std::vector<Fill> fills;
  std::vector<Fill> strokes;
  std::vector<float> stroke_widths;
  std::vector<saturn::Rect> clips;
  std::vector<State> states;
  std::vector<Effect> effects;
  void clear(saturn::Color) override {}
  void fill_rect(saturn::Rect r, saturn::Color c, float radius) override {
    fills.push_back({r,c,radius});
  }
  void stroke_rect(saturn::Rect r, saturn::Color c, float w, float radius) override {
    strokes.push_back({r,c,radius}); stroke_widths.push_back(w);
  }
  void state_layer(saturn::Rect, saturn::Color, float, float h, float p,
                   float x, float y, float radius) override { states.push_back({h,p,x,y,radius}); }
  void clip_push(saturn::Rect r) override { clips.push_back(r); }
  void clip_pop() override {}
  void effect_push(float x,float y,float alpha) override { effects.push_back({x,y,alpha}); }
  void effect_pop() override {}
  void* create_texture_rgba8(int,int,const std::uint8_t*) override { return this; }
  void draw_textured_quads(void*,const saturn::TexturedQuad*,std::size_t,saturn::Color,float) override {}
  void flip() override {}
  void on_resize(int,int) override {}
};
void trace() {
  saturn::set_default_font(saturn::Font::load_default());
  saturn::Switch toggle;
  toggle.set_rect({0,0,52,40});
  toggle.tick(10);
  toggle.set_value(true);
  std::cout << std::setprecision(12) << "{\"switch\":[";
  bool first = true;
  for (double ms : {0.,15.,33.,67.,100.,150.,200.,250.,300.}) {
    toggle.tick(10+ms/1000);
    Recorder r; toggle.paint(r);
    const auto& thumb = r.fills.back();
    const auto& track = r.fills.front();
    if (!first) std::cout << ',';
    first = false;
    std::cout << '[' << ms << ',' << thumb.rect.x+thumb.radius << ','
              << thumb.radius << ',' << int(track.color.r) << ','
              << int(track.color.g) << ',' << int(track.color.b) << ']';
  }
  std::cout << "],\"curves\":[";
  first = true;
  for (int curve = 0; curve < 8; ++curve)
    for (double t : {0.,.01,.1,.25,.5,.75,.99,1.}) {
      if (!first) std::cout << ',';
      first = false;
      std::cout << '[' << curve << ',' << t << ','
                << saturn::motion::ease(static_cast<saturn::motion::Curve>(curve),t) << ']';
    }
  std::cout << "],\"button\":[";
  saturn::FilledButton button("Filled",[]{});
  button.set_rect({0,0,100,40}); button.tick(10);
  button.on_hover(true); button.on_pointer({5,20,true});
  first = true;
  for (double ms : {15.,33.,75.,100.,150.,200.,250.,300.}) {
    button.tick(10+ms/1000);
    if (ms == 200) button.on_pointer({5,20,false,true});
    Recorder r; button.paint(r);
    if (!first) std::cout << ',';
    first = false;
    State state = r.states.empty() ? State{} : r.states.back();
    std::cout << '[' << ms << ',' << state.hover << ',' << state.press << ','
              << state.x << ',' << state.y << ',' << state.radius << ']';
  }
  std::cout << "],\"overlay\":[";
  saturn::AlertDialog dialog("Confirm","Delete?",{});
  saturn::SnackBar snack("Saved!","Undo");
  dialog.tick(10); dialog.on_shown(); dialog.set_rect({0,0,944,761}); dialog.layout();
  snack.tick(10); snack.on_shown(); snack.set_rect({0,0,944,761}); snack.layout();
  first = true;
  for (double ms : {0.,30.,75.,150.,225.,300.,330.,375.,450.,500.}) {
    dialog.tick(10+ms/1000); snack.tick(10+ms/1000);
    if (ms == 300) { dialog.begin_dismiss(); snack.begin_dismiss(); }
    Recorder dr; dialog.paint(dr);
    Recorder sr; snack.paint(sr);
    if (!first) std::cout << ',';
    first = false;
    std::cout << '[' << ms << ',' << dr.effects[0].y << ','
              << dr.effects[1].alpha << ',' << dr.effects[2].alpha << ','
              << dr.effects[3].alpha << ',' << sr.effects[0].y << ','
              << sr.effects[0].alpha << ']';
  }
  std::cout << "],\"checkbox\":[";
  saturn::Checkbox checkbox("");
  checkbox.set_rect({0,0,18,18}); checkbox.tick(10); checkbox.set_value(true);
  first = true;
  for (double ms : {0.,15.,50.,100.,150.,250.,350.,375.,400.,449.,500.}) {
    checkbox.tick(10+ms/1000);
    if (ms == 350) checkbox.set_value(false);
    Recorder r; checkbox.paint(r);
    if (!first) std::cout << ','; first = false;
    std::cout << '[' << ms << ',' << (r.fills.empty() ? 0 : r.fills[0].rect.w) << ','
              << (r.fills.empty() ? 0 : int(r.fills[0].color.a)) << ','
              << (r.strokes.empty() ? 0 : int(r.strokes[0].color.a)) << ']';
  }
  std::cout << "],\"slider\":[";
  saturn::Slider slider(0,100,10);
  slider.set_rect({0,0,300,48}); slider.tick(10);
  slider.on_pointer({150,24,true});
  first = true;
  for (double ms : {15.,50.,100.,150.,200.,225.,250.,300.,400.,600.}) {
    slider.tick(10+ms/1000);
    if (ms == 150) slider.on_pointer({150,24,false,true});
    Recorder r; slider.paint(r);
    if (!first) std::cout << ','; first = false;
    std::cout << '[' << ms << ',' << r.fills.back().rect.w << ','
              << (r.states.empty() ? 0 : r.states[0].press) << ','
              << (r.states.empty() ? 0 : r.states[0].radius) << ']';
  }
  std::cout << "],\"field\":[";
  saturn::TextField field("Name");
  field.set_rect({0,0,300,56}); field.tick(10);
  field.on_focus(true); field.on_hover(true);
  first = true;
  for (double ms : {0.,15.,50.,75.,100.,150.,200.,225.,250.,300.,350.}) {
    field.tick(10+ms/1000);
    if (ms == 200) { field.on_focus(false); field.on_hover(false); }
    Recorder r; field.paint(r);
    if (!first) std::cout << ','; first = false;
    std::cout << '[' << ms << ',' << r.stroke_widths[0] << ','
              << int(r.strokes[0].color.r) << ',' << int(r.strokes[0].color.g) << ','
              << int(r.strokes[0].color.b) << ']';
  }
  std::cout << "],\"menu\":[";
  saturn::Page menu_page; menu_page.set_padding(0);
  auto dropdown = std::make_unique<saturn::Dropdown>("Choose",
      std::vector<saturn::DropdownOption>{{"a","Alpha"},{"b","Beta"},{"g","Gamma"}});
  auto* menu = dropdown.get();
  menu_page.add(std::move(dropdown)); menu_page.layout(400,400); menu_page.tick(10);
  menu->set_open(true); first = true;
  for (double ms : {0.,15.,50.,100.,150.,200.,250.,300.,330.,375.,400.,449.}) {
    menu_page.tick(10+ms/1000);
    if (ms == 300) menu->set_open(false);
    Recorder r; menu->paint_menu(r);
    if (!first) std::cout << ','; first = false;
    std::cout << '[' << ms << ',' << r.clips.back().h << ',' << r.effects[0].alpha << ',';
    for (int i = 0; i < 3; ++i) {
      if (i) std::cout << ',';
      const float alpha = std::size_t(i+1) < r.effects.size() ? r.effects[i+1].alpha : 0;
      std::cout << alpha;
    }
    std::cout << ']';
  }
  std::cout << "],\"scrollbar\":[";
  saturn::ControlOptions list_opt; list_opt.width = 100.f; list_opt.height = 100.f;
  saturn::ListView list(4,list_opt); list.set_rect({0,0,100,100});
  for (int i = 0; i < 30; ++i) {
    saturn::ControlOptions opt; opt.height = 30.f;
    list.add(std::make_unique<saturn::ColorBox>(saturn::colors::kPrimary,opt));
  }
  list.layout(); list.tick(10); list.on_scroll({20,20,-1}); first = true;
  for (double ms : {15.,50.,100.,200.,250.,300.,400.,450.,500.,999.,1000.,1050.,1125.,1250.}) {
    list.tick(10+ms/1000);
    if (ms == 200) list.on_hover(true);
    if (ms == 400) list.on_hover(false);
    Recorder r; list.paint(r);
    if (!first) std::cout << ','; first = false;
    const bool drawn = !r.fills.empty() && r.fills.back().color.a != 255;
    std::cout << '[' << ms << ',' << (drawn ? r.fills.back().rect.w : 8) << ','
              << (drawn ? int(r.fills.back().color.a) : 0) << ']';
  }
  std::cout << "],\"interruption\":[";
  first = true;
  for (int curve = 0; curve < 8; ++curve) {
    saturn::motion::Tween tween;
    tween.animate(1,300,static_cast<saturn::motion::Curve>(curve),10);
    for (double ms : {0.,50.,90.,120.,150.,180.,210.,240.,300.,450.}) {
      if (ms == 90) tween.animate(0,150,static_cast<saturn::motion::Curve>(curve),10.09);
      if (ms == 150) tween.animate(1,300,static_cast<saturn::motion::Curve>(curve),10.15);
      if (!first) std::cout << ','; first = false;
      std::cout << '[' << curve << ',' << ms << ',' << tween.value(10+ms/1000) << ']';
    }
  }
  std::cout << "]}\n";
}
void test() {
  using namespace saturn;
  set_default_font(Font::load_default());
  motion::Tween tween;
  tween.animate(1,100, motion::Curve::Linear,10);
  require(std::abs(tween.value(10.05)-.5) < 1e-8,"linear tween");
  tween.animate(0,100, motion::Curve::Linear,10.05);
  require(std::abs(tween.value(10.1)-.25) < 1e-8,"continuous reversal");
  require(tween.value(11) == 0,"tween completion");
  int changes = 0;
  Switch toggle(false,[&](bool) { ++changes; });
  toggle.set_rect({0,0,52,40}); toggle.tick(10);
  toggle.on_pointer({16,20,true});
  toggle.on_pointer({16,20,false,true});
  require(toggle.value() && changes == 1,"switch click callback");
  toggle.tick(10.1); Recorder r; toggle.paint(r);
  require(r.fills.back().radius > 8 && r.fills.back().radius < 12,"switch size transition");
  toggle.tick(11); toggle.set_value(false);
  require(changes == 1,"programmatic switch setter must not emit change");
  toggle.tick(12);
  toggle.on_pointer({16,20,true});
  toggle.on_pointer({36,20,false,false,true});
  toggle.on_pointer({36,20,false,true});
  require(toggle.value() && changes == 2,"switch drag");
  toggle.on_pointer({16,20,true});
  toggle.on_pointer({0,0,false,false,false,true});
  toggle.on_pointer({16,20,false,true});
  require(changes == 2,"cancelled switch press");

  Page page; page.set_padding(0);
  std::string changed, submitted;
  auto field = std::make_unique<TextField>("Name",
      [&](const std::string& s) { changed = s; },
      [&](const std::string& s) { submitted = s; });
  auto* editor = field.get(); page.add(std::move(field)); page.layout(400,300); page.tick(10);
  page.dispatch_pointer({20,20,true});
  page.dispatch_pointer({20,20,false,true});
  page.dispatch_text({"abc"});
  require(editor->value() == "abc" && changed == "abc","text input routing");
  page.dispatch_key({Key::Left}); page.dispatch_key({Key::Backspace});
  require(editor->value() == "ac","caret backspace");
  page.dispatch_key({Key::A,false,true}); page.dispatch_text({"\xc3\xa9"});
  require(editor->value() == "\xc3\xa9","selection replacement UTF-8");
  page.dispatch_key({Key::Backspace});
  require(editor->value().empty(),"UTF-8 codepoint deletion");
  page.dispatch_text({"Saturn"}); page.dispatch_key({Key::Enter});
  require(submitted == "Saturn","submit callback");
  const auto before = editor->value();
  bool rejected = false;
  try { editor->set_value(std::string(kMaxTextLen+1,'a')); }
  catch (const std::invalid_argument&) { rejected = true; }
  require(rejected && editor->value() == before,"text cap strong guarantee");
  page.dispatch_pointer({390,290,true}); page.dispatch_text({"ignored"});
  require(editor->value() == before,"outside focus dismiss");
  page.dispatch_key({Key::Tab}); page.dispatch_text({"!"});
  require(editor->value() == "Saturn!","tab focus routing");
  int clicks = 0;
  auto button = std::make_unique<FilledButton>("Click",[&] { ++clicks; });
  page.add(std::move(button)); page.layout(400,300);
  page.dispatch_key({Key::Tab}); page.dispatch_key({Key::Enter});
  require(clicks == 1,"keyboard button activation");
  editor->on_focus(true);
  std::string clipboard;
  editor->set_clipboard_handlers([&] { return clipboard; },
      [&](std::string_view s) { clipboard = s; return true; });
  editor->set_value("one two, three");
  editor->on_key({Key::Left,false,true});
  editor->on_key({Key::Backspace,false,true});
  require(editor->value() == "one twothree","Ctrl backspace uses Python word boundary");
  editor->on_key({Key::Home}); editor->on_key({Key::Right,true,true});
  editor->on_key({Key::C,false,true});
  require(clipboard == "one","copy selected word");
  editor->on_key({Key::X,false,true});
  require(editor->value() == " twothree","cut selection");
  clipboard = "Saturn\r\n!";
  editor->on_key({Key::A,false,true}); editor->on_key({Key::V,false,true});
  require(editor->value() == "Saturn!","paste removes single-line newlines");
  editor->set_value("a");
  editor->on_composition({"ni",1,1});
  editor->on_key({Key::Backspace});
  require(editor->value() == "a","IME owns editing until commit");
  require(editor->text_input_area().has_value(),"IME candidate anchor available");
  editor->on_text({"\xe4\xbd\xa0"});
  require(editor->value() == "a\xe4\xbd\xa0","IME commit only updates value once");
  editor->on_composition({"x",0,1});
  editor->on_focus(false); editor->on_focus(true);
  editor->on_key({Key::Backspace});
  require(editor->value() == "a","blur clears composition");
  bool bad_utf8 = false;
  try { editor->on_text({"\xc0\xaf"}); } catch (const std::invalid_argument&) { bad_utf8 = true; }
  require(bad_utf8 && editor->value() == "a","invalid UTF-8 rejected before edit");
  auto dropdown = std::make_unique<Dropdown>("Choose",
      std::vector<DropdownOption>{{"a","Alpha"},{"b","Beta"}});
  auto* menu = dropdown.get();
  page.add(std::move(dropdown)); page.layout(400,300); page.tick(20);
  const auto height = menu->intrinsic({},{}).h;
  menu->set_open(true); page.tick(20.3);
  require(menu->intrinsic({},{}).h == height,"menu must not expand layout");
  menu->on_key({Key::Down}); menu->on_key({Key::Enter});
  require(menu->value() == "b" && !menu->is_open(),"keyboard menu selection");
  menu->set_open(true); page.tick(21);
  page.dispatch_pointer({390,290,true});
  require(!menu->is_open(),"outside menu dismissal");

  auto dialog = std::make_unique<AlertDialog>("Confirm","Delete?",
      std::vector<std::unique_ptr<Control>>{});
  auto* dialog_ptr = dialog.get();
  page.tick(30); page.show_dialog(std::move(dialog)); page.layout(400,300);
  page.tick(30.3); page.pop_dialog(dialog_ptr); page.tick(30.3);
  require(dialog_ptr->closing() && !dialog_ptr->ready_to_remove(),"dialog deferred exit animation");
  page.tick(30.5);

  ControlOptions list_options; list_options.width = 100.f; list_options.height = 100.f;
  ListView list(4,list_options); list.set_rect({0,0,100,100});
  for (int i = 0; i < 30; ++i) {
    ControlOptions row; row.width = 100.f; row.height = 30.f;
    list.add(std::make_unique<ColorBox>(colors::kPrimary,row));
  }
  list.layout(); list.tick(10);
  require(list.on_scroll({20,20,-2}) && list.scroll_offset() == 80,"wheel scroll");
  list.on_scroll({20,20,-10000});
  require(list.scroll_offset() == 916,"scroll lower bound");
  list.on_scroll({20,20,10000});
  require(list.scroll_offset() == 0,"scroll upper bound");
  require(!list.hit_target(20,110),"ListView clips hit targets");
  Recorder visible; list.paint(visible);
  require(visible.fills.size() <= 4,"ListView only paints visible rows");
  Page guarded; guarded.set_padding(0); guarded.tick(40);
  int guarded_clicks = 0;
  auto parent = std::make_unique<Container>();
  auto* parent_ptr = parent.get();
  auto nested_button = std::make_unique<FilledButton>("Click",[&] { ++guarded_clicks; });
  auto* child_ptr = nested_button.get(); parent->add(std::move(nested_button));
  guarded.add(std::move(parent)); guarded.layout(400,300);
  guarded.dispatch_pointer({30,20,true});
  ControlOptions disabled; disabled.disabled = true; parent_ptr->set_options(disabled);
  guarded.tick(40.1);
  guarded.dispatch_pointer({30,20,false,true});
  require(guarded_clicks == 0,"disabled ancestor cancels pointer capture");
  parent_ptr->set_options({});
  guarded.dispatch_pointer({30,20,false,true});
  require(guarded_clicks == 0,"reenabled subtree must not retain stale press");
  guarded.dispatch_key({Key::Tab});
  parent_ptr->set_options(disabled); guarded.dispatch_key({Key::Enter});
  require(guarded_clicks == 0,"disabled ancestor cancels focus");
  parent_ptr->set_options({});
  guarded.dispatch_key({Key::Tab}); guarded.dispatch_key({Key::Enter});
  require(guarded_clicks == 1,"recovered subtree receives fresh focus");

  Page modal_page; modal_page.set_padding(0); modal_page.tick(50);
  auto modal_list = std::make_unique<ListView>(4.f,list_options);
  auto* modal_list_ptr = modal_list.get();
  for (int i = 0; i < 30; ++i) {
    ControlOptions opt; opt.height = 30.f;
    modal_list->add(std::make_unique<ColorBox>(colors::kPrimary,opt));
  }
  modal_page.add(std::move(modal_list)); modal_page.layout(400,300);
  auto modal = std::make_unique<AlertDialog>("Modal","Blocked",
      std::vector<std::unique_ptr<Control>>{},true);
  auto* modal_ptr = modal.get(); modal_page.show_dialog(std::move(modal));
  modal_page.layout(400,300); modal_page.tick(50.3);
  modal_page.dispatch_scroll({20,20,-2});
  require(modal_list_ptr->scroll_offset() == 0,"modal barrier blocks scroll");
  modal_page.pop_dialog(modal_ptr); modal_page.tick(50.3);
  modal_page.dispatch_scroll({20,20,-2});
  require(modal_list_ptr->scroll_offset() == 0,"closing barrier still blocks scroll");
  modal_page.tick(50.5); modal_page.dispatch_scroll({20,20,-2});
  require(modal_list_ptr->scroll_offset() == 80,"scroll resumes after modal exit");

  ListView track(4,list_options); track.set_rect({0,0,100,100});
  for (int i = 0; i < 30; ++i) {
    ControlOptions opt; opt.height = 30.f;
    track.add(std::make_unique<ColorBox>(colors::kPrimary,opt));
  }
  track.layout(); track.tick(60);
  track.on_pointer({95,50,true});
  require(std::abs(track.scroll_offset()-458) < .01,"track click centers thumb");
  track.on_pointer({95,100,false,false,true});
  require(track.scroll_offset() == 916,"scrollbar drag clamps");
  track.on_pointer({95,100,false,true});
  track.tick(60.7); track.tick(61);
  Recorder faded; track.paint(faded);
  require(faded.fills.back().color.a == 255,"scrollbar fades after drag release");
  Page timeout_page; timeout_page.tick(70); timeout_page.layout(400,300);
  auto timeout_snack = std::make_unique<SnackBar>("Timeout","",std::function<void()>{},1000);
  auto* timeout_ptr = timeout_snack.get();
  timeout_page.show_dialog(std::move(timeout_snack)); timeout_page.layout(400,300);
  timeout_page.tick(70.999);
  require(!timeout_ptr->closing(),"snackbar keeps deadline before duration");
  timeout_page.tick(71);
  require(timeout_ptr->closing() && !timeout_ptr->ready_to_remove(),"snackbar duration starts animated dismissal");
  timeout_page.tick(71.25);
  std::cout << "behavior tests passed\n";
}
}
int main(int argc,char** argv) {
  try {
    if (argc > 1 && std::string(argv[1]) == "--trace") trace();
    else test();
    return 0;
  } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
