cmake_minimum_required(VERSION 3.20)
project(saturn_cpp LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Prefer SDL3Config from CMAKE_PREFIX_PATH (e.g. SDL3-devel VC layout).
find_package(SDL3 REQUIRED CONFIG)

add_library(saturn
  src/app.cpp src/window.cpp src/page.cpp src/control.cpp src/opengl_renderer.cpp)
target_include_directories(saturn PUBLIC include PRIVATE src)
target_link_libraries(saturn PUBLIC SDL3::SDL3)
if (WIN32)
  target_link_libraries(saturn PUBLIC opengl32)
endif()

add_executable(saturn_hello src/main.cpp)
target_link_libraries(saturn_hello PRIVATE saturn)

# Copy SDL3.dll next to the exe on Windows when known.
if (WIN32 AND DEFINED SDL3_DIR)
  get_filename_component(_sdl3_root "${SDL3_DIR}/../.." ABSOLUTE)
  if (EXISTS "${_sdl3_root}/lib/x64/SDL3.dll")
    add_custom_command(TARGET saturn_hello POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${_sdl3_root}/lib/x64/SDL3.dll" $<TARGET_FILE_DIR:saturn_hello>)
  endif()
endif()
