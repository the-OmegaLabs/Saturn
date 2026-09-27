// Shared analytic effects. Coordinates and widths are logical pixels.
float shadow_shape_distance(vec2 p, vec2 size, vec4 radii) {
    float radius = p.y < size.y * .5 ?
        (p.x < size.x * .5 ? radii.x : radii.y) :
        (p.x < size.x * .5 ? radii.w : radii.z);
    radius = clamp(radius, 0.0, min(size.x, size.y) * .5);
    vec2 q = abs(p - size * .5) - size * .5 + radius;
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - radius;
}

float gaussian_shadow(float distance, float sigma) {
    // Normal cumulative distribution, approximated without a blur texture.
    float x = abs(distance) / max(sigma, .001);
    float t = 1.0 / (1.0 + .2316419 * x);
    float tail = .39894228 * exp(-.5*x*x) * t *
        (.31938153 + t * (-.35656378 + t *
         (1.78147794 + t * (-1.82125598 + t * 1.33027443))));
    return distance >= 0.0 ? tail : 1.0-tail;
}

float elevation_shadow(vec2 p, vec2 size, vec4 radii, vec4 info) {
    p -= vec2(info.w);
    size -= vec2(info.w * 2.0);
    float ambient = gaussian_shadow(shadow_shape_distance(p, size, radii), info.x) * (28.0/255.0);
    float key = gaussian_shadow(shadow_shape_distance(p-vec2(0,info.z), size, radii), info.y) * (40.0/255.0);
    return key + ambient * (1.0-key);
}

float wave_line_distance(vec2 p, vec4 wave, vec4 info) {
    float a = wave.x;
    float b = wave.y;
    float amplitude = wave.z;
    float wavelength = max(wave.w, 0.001);
    float x = clamp(p.x, a, b);
    float taper = clamp(min((x-a), (b-x)) / (wavelength * .25), 0.0, 1.0);
    float angle = x / wavelength * 6.28318530718 - info.x;
    float y = info.z + amplitude * taper * sin(angle);
    float taper_slope = taper < 1.0 ? (x-a < b-x ? 4.0 : -4.0) / wavelength : 0.0;
    float slope = amplitude * (taper_slope * sin(angle) +
                              taper * cos(angle) * 6.28318530718 / wavelength);
    // Project onto the local tangent. Endpoints keep circular stroke caps.
    float d = p.x < a || p.x > b ? length(p - vec2(x, y)) :
              abs(p.y-y) / sqrt(1.0+slope*slope);
    return d - info.y * .5;
}

float wave_arc_distance(vec2 p, vec4 wave, vec4 info) {
    float radius = wave.x;
    float start = wave.y;
    float sweep = clamp(wave.z, 0.0, 6.28318530718);
    float amplitude = wave.w;
    float theta = atan(p.y, p.x);
    float relative = mod(theta - start, 6.28318530718);
    float angle = start + relative;
    float r = radius + amplitude * sin(angle * info.z - info.x);
    float derivative = amplitude * info.z * cos(angle * info.z - info.x);
    float d = abs(length(p)-r) / sqrt(1.0+derivative*derivative / max(r*r, .001));
    if (relative > sweep && sweep < 6.283184) {
        vec2 first = vec2(cos(start), sin(start)) *
                     (radius+amplitude*sin(start*info.z-info.x));
        float end = start+sweep;
        vec2 last = vec2(cos(end), sin(end)) *
                    (radius+amplitude*sin(end*info.z-info.x));
        d = min(length(p-first), length(p-last));
    }
    return d - info.y * .5;
}
