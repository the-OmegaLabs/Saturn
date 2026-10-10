cmake_minimum_required(VERSION 3.20)
project(saturn_cpp LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Prefer SDL3Config from CMAKE_PREFIX_PATH (e.g. SDL3-devel VC layout).
find_package(SDL3 REQUIRED CONFIG)

add_library(saturn
  src/app.cpp src/window.cpp src/page.cpp src/control.cpp src/inputs.cpp src/font.cpp
  src/opengl_renderer.cpp src/renderer_default.cpp)
target_include_directories(saturn PUBLIC include PRIVATE src third_party)
target_link_libraries(saturn PUBLIC SDL3::SDL3)
if (MSVC)
  target_compile_options(saturn PUBLIC /utf-8)
endif()
if (WIN32)
  target_link_libraries(saturn PUBLIC opengl32)
elseif (UNIX AND NOT APPLE)
  # Mesa / system libGL (needed for OpenGLRenderer symbols on Linux).
  target_link_libraries(saturn PUBLIC GL)
endif()

add_executable(saturn_hello src/main.cpp)
target_link_libraries(saturn_hello PRIVATE saturn)

add_executable(saturn_demo src/demo_main.cpp)
target_link_libraries(saturn_demo PRIVATE saturn)
add_executable(saturn_counter examples/counter.cpp)
target_link_libraries(saturn_counter PRIVATE saturn)
set(_runtime_targets saturn_hello saturn_demo saturn_counter)

include(CTest)
if (BUILD_TESTING)
  add_executable(saturn_behavior_tests tests/behavior.cpp)
  target_link_libraries(saturn_behavior_tests PRIVATE saturn)
  add_executable(saturn_visual_frames tests/visual_frames.cpp)
  target_link_libraries(saturn_visual_frames PRIVATE saturn)
  target_include_directories(saturn_visual_frames PRIVATE third_party)
  add_executable(saturn_antialias_tests tests/antialias_gpu.cpp)
  target_link_libraries(saturn_antialias_tests PRIVATE saturn)
  target_include_directories(saturn_antialias_tests PRIVATE third_party)
  add_test(NAME saturn_antialias_gpu COMMAND saturn_antialias_tests)
  list(APPEND _runtime_targets saturn_behavior_tests saturn_visual_frames saturn_antialias_tests)
  add_test(NAME saturn_behavior COMMAND saturn_behavior_tests)
  set_tests_properties(saturn_behavior PROPERTIES
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}/.."
    ENVIRONMENT "SATURN_FONT_PATH=${CMAKE_SOURCE_DIR}/assets/Inter-Regular.ttf")
endif()

# Copy SDL3.dll next to the exes on Windows when known.
if (WIN32 AND DEFINED SDL3_DIR)
  get_filename_component(_sdl3_root "${SDL3_DIR}/../.." ABSOLUTE)
  if (EXISTS "${_sdl3_root}/lib/x64/SDL3.dll")
    foreach(_tgt ${_runtime_targets})
      add_custom_command(TARGET ${_tgt} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${_sdl3_root}/lib/x64/SDL3.dll" $<TARGET_FILE_DIR:${_tgt}>)
    endforeach()
  endif()
endif()

# Bundled Inter Regular (OFL) + logo next to both exes.
foreach(_tgt ${_runtime_targets})
  add_custom_command(TARGET ${_tgt} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:${_tgt}>/assets"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "${CMAKE_SOURCE_DIR}/assets/Inter-Regular.ttf"
      "$<TARGET_FILE_DIR:${_tgt}>/assets/Inter-Regular.ttf"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "${CMAKE_SOURCE_DIR}/../.static/saturn-logo-transparent.png"
      "$<TARGET_FILE_DIR:${_tgt}>/assets/saturn-logo-transparent.png"
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:${_tgt}>/assets/icons"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "${CMAKE_SOURCE_DIR}/assets/icons/favorite.png"
      "$<TARGET_FILE_DIR:${_tgt}>/assets/icons/favorite.png"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "${CMAKE_SOURCE_DIR}/assets/icons/check.png"
      "$<TARGET_FILE_DIR:${_tgt}>/assets/icons/check.png"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "${CMAKE_SOURCE_DIR}/assets/icons/add.png"
      "$<TARGET_FILE_DIR:${_tgt}>/assets/icons/add.png"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "${CMAKE_SOURCE_DIR}/../examples/assets/test_img.png"
      "$<TARGET_FILE_DIR:${_tgt}>/assets/test_img.png")
endforeach()
