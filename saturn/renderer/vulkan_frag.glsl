#version 450

layout(set = 0, binding = 0) uniform sampler2D image_texture;

layout(location = 0) in vec2 in_uv;
layout(location = 1) in vec2 in_half_size;
layout(location = 2) in float in_radius;
layout(location = 3) in float in_border_width;
layout(location = 4) in vec4 in_color;
layout(location = 5) in vec4 in_border_color;
layout(location = 6) in float in_mode;
layout(location = 7) in vec4 in_state_radii;
layout(location = 8) in vec4 in_state_info;
layout(location = 0) out vec4 out_color;

void main() {
    if (in_mode > 1.5) {
        vec2 size = in_half_size * 2.0;
        vec2 point = in_uv * size;
        // Radii are ordered TL, TR, BR, BL like Saturn's shape masks.
        float corner_radius = point.y < in_half_size.y
            ? (point.x < in_half_size.x ? in_state_radii.x : in_state_radii.y)
            : (point.x < in_half_size.x ? in_state_radii.w : in_state_radii.z);
        corner_radius = clamp(corner_radius, 0.0,
                              min(in_half_size.x, in_half_size.y));
        vec2 q = abs(point - in_half_size) -
                 (in_half_size - corner_radius);
        float distance = length(max(q, 0.0)) +
                         min(max(q.x, q.y), 0.0) - corner_radius;
        // OpenGL renders to a 2x target before downsampling. At a direct
        // swapchain resolution, 0.65 pixel derivatives match that coverage.
        float shape_feather = max(0.65 * fwidth(distance), 0.001);
        float mask = 1.0 - smoothstep(
            -shape_feather, shape_feather, distance);
        float ripple_distance = length(point - in_state_info.xy);
        float ripple_feather = max(0.65 * fwidth(ripple_distance), 0.001);
        float ripple = 1.0 - smoothstep(
            -ripple_feather, ripple_feather,
            ripple_distance - in_state_info.z);
        float hover = clamp(in_border_width, 0.0, 1.0);
        float pressed = clamp(in_state_info.w, 0.0, 1.0) * ripple;
        float opacity = hover + pressed * (1.0 - hover);
        out_color = vec4(in_color.rgb, in_color.a * opacity * mask);
        return;
    }
    if (in_mode > 0.5) {
        out_color = texture(image_texture, in_uv) * in_color;
        return;
    }
    if (in_radius < 0.0) {
        out_color = in_color;
        return;
    }
    vec2 local = (in_uv * 2.0 - 1.0) * in_half_size;
    float radius = min(in_radius, min(in_half_size.x, in_half_size.y));
    vec2 q = abs(local) - (in_half_size - radius);
    float distance = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
    float feather = max(0.65 * fwidth(distance), 0.001);
    float outer = 1.0 - smoothstep(-feather, feather, distance);
    if (in_border_width <= 0.0) {
        out_color = vec4(in_color.rgb, in_color.a * outer);
        return;
    }
    float inner = 1.0 - smoothstep(
        -feather, feather, distance + in_border_width);
    float border = max(0.0, outer - inner);
    float alpha = in_color.a * inner + in_border_color.a * border;
    if (alpha <= 0.0) {
        out_color = vec4(0.0);
        return;
    }
    vec3 rgb = (in_color.rgb * in_color.a * inner +
                in_border_color.rgb * in_border_color.a * border) / alpha;
    out_color = vec4(rgb, alpha);
}
