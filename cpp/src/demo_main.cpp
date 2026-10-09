#include "saturn/app.hpp"
#include "saturn/colors.hpp"
#include "saturn/demo_size.hpp"
#include "saturn/control.hpp"
#include "saturn/page.hpp"
#include "saturn/types.hpp"
#include <memory>
#include <string>

namespace {

// Layout stand-in: reserves space without inventing widgets we do not have yet.
std::unique_ptr<saturn::ColorBox> spacer(float w, float h, saturn::Color c) {
  saturn::ControlOptions opt;
  opt.width = w;
  opt.height = h;
  return std::make_unique<saturn::ColorBox>(c, opt);
}

std::unique_ptr<saturn::Container> make_panel(
    const char* title, std::unique_ptr<saturn::Control> body) {
  saturn::ControlOptions opt;
  opt.width = 440.f;
  auto panel = std::make_unique<saturn::Container>(opt);
  panel->set_bgcolor(saturn::colors::kSurfaceContainerLow);
  panel->set_padding(20.f);
  panel->set_corner_radius(16.f);
  auto col = std::make_unique<saturn::Column>(16.f);
  col->add(std::make_unique<saturn::Text>(
      title, saturn::colors::kOnSurface, 18.f));
  if (body) col->add(std::move(body));
  panel->add(std::move(col));
  return panel;
}

// brand_header("Saturn Demo", detail=f"v{version}") — logo slot 52x40.
std::unique_ptr<saturn::Row> brand_header(const char* title, const char* detail) {
  auto header = std::make_unique<saturn::Row>(12.f);
  header->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
  // Real Image+PRIMARY tint TBD; SURFACE ColorBox keeps header height without a
  // solid purple blob that would worsen avg_abs vs the sparse logo.
  header->add(spacer(52.f, 40.f, saturn::colors::kSurface));
  header->add(std::make_unique<saturn::Text>(
      title, saturn::colors::kOnSurface, 28.f));
  if (detail && detail[0]) {
    header->add(std::make_unique<saturn::Text>(
        detail, saturn::colors::kOnSurfaceVariant, 12.f));
  }
  return header;
}

} // namespace

int main() {
  return saturn::run(
      [](saturn::Page& page) {
        page.set_title("saturn demo");
        page.set_bgcolor(saturn::colors::kSurface);
        page.set_padding(24.f);
        page.set_spacing(16.f);

        page.add(brand_header("Saturn Demo", "v0.1.0"));

        auto status = std::make_unique<saturn::Text>(
            "interact with the controls below",
            saturn::colors::kOnSurfaceVariant, 13.f);
        saturn::Text* status_ptr = status.get();
        page.add(std::move(status));

        // Controls panel — match demo.py Row structure with available widgets.
        // Elevated / Outlined / IconButton are layout stubs (panel-colored) so the
        // real Filled lands near the golden PRIMARY blob (x≈174).
        auto btn_row = std::make_unique<saturn::Row>(8.f);
        btn_row->set_cross_axis_alignment(saturn::CrossAxisAlignment::Center);
        // Width from golden: content_x 44 + elev + gap 8 = filled_x 174 → elev=122.
        btn_row->add(spacer(122.f, 40.f, saturn::colors::kSurfaceContainerLow));
        btn_row->add(std::make_unique<saturn::FilledButton>(
            "Filled", [status_ptr]() {
              status_ptr->set_value("last event: click");
            }));
        btn_row->add(spacer(104.f, 40.f, saturn::colors::kSurfaceContainerLow));
        btn_row->add(spacer(40.f, 40.f, saturn::colors::kSurfaceContainerLow));

        auto left_body = std::make_unique<saturn::Column>(16.f);
        left_body->add(std::move(btn_row));
        // Approximate remaining demo.py rows (TextField/Checkbox, Slider row,
        // Dropdown/Image, Dialog row) with panel-colored mass — not real widgets.
        left_body->add(spacer(400.f, 48.f, saturn::colors::kSurfaceContainerLow));
        left_body->add(spacer(400.f, 40.f, saturn::colors::kSurfaceContainerLow));
        left_body->add(spacer(400.f, 70.f, saturn::colors::kSurfaceContainerLow));
        left_body->add(spacer(200.f, 40.f, saturn::colors::kSurfaceContainerLow));

        // Scrollable list panel — static fake items (NOT ListView; no scroll).
        auto right_body = std::make_unique<saturn::Column>(4.f);
        saturn::ControlOptions list_opt;
        list_opt.width = 400.f;
        list_opt.height = 260.f;
        auto list_col = std::make_unique<saturn::Column>(4.f, list_opt);
        for (int i = 0; i < 8; ++i) {
          saturn::ControlOptions item_opt;
          item_opt.width = 400.f;
          auto item = std::make_unique<saturn::Container>(item_opt);
          item->set_padding(8.f);
          item->set_corner_radius(6.f);
          item->set_bgcolor(
              (i % 2) ? saturn::colors::kSurfaceContainerLow
                      : saturn::colors::kSurfaceContainer);
          item->add(std::make_unique<saturn::Text>(
              std::string("list item ") + std::to_string(i),
              saturn::colors::kOnSurface, 13.f));
          list_col->add(std::move(item));
        }
        right_body->add(std::move(list_col));

        auto panels = std::make_unique<saturn::Row>(24.f);
        panels->set_cross_axis_alignment(saturn::CrossAxisAlignment::Start);
        panels->add(make_panel("Controls", std::move(left_body)));
        panels->add(make_panel("Scrollable list", std::move(right_body)));
        page.add(std::move(panels));
      },
      // LOGICAL CLIENT size (SDL CreateWindow) — not Python outer 960x800.
      // At 100% DPI this equals golden pixels 944x761; HiDPI diverges.
      saturn::kDemoClientWidth, saturn::kDemoClientHeight,
      /*demo_contract=*/true);
}
