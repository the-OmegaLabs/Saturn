// Portable procedural fragments shared by OpenGL and Vulkan. Coordinates are
// normalized inside the control; all colors use straight alpha.
float effect_hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float effect_noise(vec2 p) {
    vec2 cell = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(effect_hash(cell), effect_hash(cell + vec2(1.0, 0.0)), f.x),
               mix(effect_hash(cell + vec2(0.0, 1.0)),
                   effect_hash(cell + vec2(1.0, 1.0)), f.x), f.y);
}

vec4 procedural_effect(vec2 uv, vec2 size, float mode, vec4 first,
                       vec4 second, vec4 parameters, vec4 information) {
    float elapsed = parameters.x;
    float strength = clamp(parameters.y, 0.0, 1.0);
    float frequency = max(parameters.z, 0.001);
    vec2 center = information.xy;
    float angle = information.z;
    vec2 p = uv - center;
    // Preserve circular rings when the control is not square.
    vec2 aspect = size / max(min(size.x, size.y), 0.001);
    float baseline = clamp(dot(p, vec2(cos(angle), sin(angle))) + 0.5, 0.0, 1.0);
    float value;
    if (mode < 0.5) {
        float animated_angle = angle + elapsed * 0.25;
        value = clamp(dot(p, vec2(cos(animated_angle), sin(animated_angle))) +
                      0.5, 0.0, 1.0);
    } else if (mode < 1.5) {
        vec2 sample_pos = uv * aspect * frequency + vec2(elapsed * .18, elapsed * .11);
        value = .57 * effect_noise(sample_pos) +
                .28 * effect_noise(sample_pos * 2.03) +
                .15 * effect_noise(sample_pos * 4.07);
    } else if (mode < 2.5) {
        float phase = length(p * aspect) * frequency * 6.28318530718 - elapsed * 2.0;
        // Fade frequencies above the fragment Nyquist limit instead of aliasing.
        float attenuation = 1.0 - smoothstep(1.2, 3.14159265359, fwidth(phase));
        value = 0.5 + 0.5 * sin(phase) * attenuation;
    } else {
        vec2 q = p * aspect * frequency;
        value = .5 + (sin(q.x + elapsed) + sin(q.y - elapsed * .7) +
                      sin((q.x + q.y) * .7 + elapsed * .4)) / 6.0;
    }
    value = mix(baseline, clamp(value, 0.0, 1.0), strength);
    // Interpolate premultiplied colors, then convert back for normal blending.
    float alpha = mix(first.a, second.a, value);
    vec3 rgb = mix(first.rgb * first.a, second.rgb * second.a, value) /
               max(alpha, 0.00001);
    float radius = clamp(parameters.w, 0.0, min(size.x, size.y) * .5);
    vec2 local = (uv - .5) * size;
    vec2 q = abs(local) - (size * .5 - radius);
    float distance = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
    float feather = max(.65 * fwidth(distance), .001);
    float coverage = 1.0 - smoothstep(-feather, feather, distance);
    return vec4(rgb, alpha * coverage);
}
