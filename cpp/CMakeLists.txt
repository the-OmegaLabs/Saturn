cmake_minimum_required(VERSION 3.20)
project(saturn_cpp LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Prefer SDL3Config from CMAKE_PREFIX_PATH (e.g. SDL3-devel VC layout).
find_package(SDL3 REQUIRED CONFIG)

add_library(saturn
  src/app.cpp src/window.cpp src/page.cpp src/control.cpp src/font.cpp
  src/opengl_renderer.cpp src/renderer_default.cpp)
target_include_directories(saturn PUBLIC include PRIVATE src third_party)
target_link_libraries(saturn PUBLIC SDL3::SDL3)
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

# Copy SDL3.dll next to the exes on Windows when known.
if (WIN32 AND DEFINED SDL3_DIR)
  get_filename_component(_sdl3_root "${SDL3_DIR}/../.." ABSOLUTE)
  if (EXISTS "${_sdl3_root}/lib/x64/SDL3.dll")
    foreach(_tgt saturn_hello saturn_demo)
      add_custom_command(TARGET ${_tgt} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${_sdl3_root}/lib/x64/SDL3.dll" $<TARGET_FILE_DIR:${_tgt}>)
    endforeach()
  endif()
endif()

# Bundled Inter Regular (OFL) + logo next to both exes.
foreach(_tgt saturn_hello saturn_demo)
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
      "${CMAKE_SOURCE_DIR}/assets/test_img.png"
      "$<TARGET_FILE_DIR:${_tgt}>/assets/test_img.png")
endforeach()
