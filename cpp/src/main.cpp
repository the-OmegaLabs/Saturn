#include "saturn/app.hpp"
#include "saturn/page.hpp"
// Phase ①: empty window. Phase ④ will add Text/FilledButton.
int main() {
  return saturn::run([](saturn::Page& page) {
    page.set_title("Saturn C++ hello");
  });
}
