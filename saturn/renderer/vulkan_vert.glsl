#version 450

layout(location = 0) in vec2 in_position;
layout(location = 1) in vec2 in_uv;
layout(location = 2) in vec2 in_half_size;
layout(location = 3) in float in_radius;
layout(location = 4) in float in_border_width;
layout(location = 5) in vec4 in_color;
layout(location = 6) in vec4 in_border_color;
layout(location = 7) in float in_mode;
layout(location = 8) in vec4 in_state_radii;
layout(location = 9) in vec4 in_state_info;

layout(location = 0) out vec2 out_uv;
layout(location = 1) out vec2 out_half_size;
layout(location = 2) out float out_radius;
layout(location = 3) out float out_border_width;
layout(location = 4) out vec4 out_color;
layout(location = 5) out vec4 out_border_color;
layout(location = 6) out float out_mode;
layout(location = 7) out vec4 out_state_radii;
layout(location = 8) out vec4 out_state_info;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    out_uv = in_uv;
    out_half_size = in_half_size;
    out_radius = in_radius;
    out_border_width = in_border_width;
    out_color = in_color;
    out_border_color = in_border_color;
    out_mode = in_mode;
    out_state_radii = in_state_radii;
    out_state_info = in_state_info;
}
