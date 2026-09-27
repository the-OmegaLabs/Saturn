// Adapted from Orb effect.wgsl, Copyright (c) 2026 LerSent001.
// MIT License: see ORB-LICENSE.txt in this directory.
// Original project: https://github.com/LerSent001/orb
float lqHash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += vec2(dot(p, p + vec2(45.32)));
    return fract(p.x * p.y);
}
float lqNoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(lqHash(i), lqHash(i+vec2(1,0)), f.x),
               mix(lqHash(i+vec2(0,1)), lqHash(i+vec2(1,1)), f.x), f.y);
}
vec2 lqFbm(vec2 p, float bs) {
    float s=0.0, a=0.5, m=0.0, vr=0.0, g=1.0;
    float e=-6.0*bs*bs;
    for (int i=0; i<5; ++i) {
        float b=exp(e*g);
        s+=a*(0.5+b*(lqNoise(p)-0.5));
        vr+=a*a*(1.0-b*b);
        m+=a;
        a*=0.5;
        g*=4.1209;
        p=mat2(.8,.6,-.6,.8)*p*2.03;
    }
    return vec2(s/m, .32*sqrt(vr)/m);
}
