// Aurora Veil and glass shell adapted from Orb effect.wgsl.
// Copyright (c) 2026 LerSent001. MIT License: ORB-LICENSE.txt.
// Original project: https://github.com/LerSent001/orb
// This single-pass adaptation does not implement the particle-ribbon pipeline.
#include "orb-noise.glsl"
uniform float orb_radius;
uniform float zoom;
uniform float warp;
uniform float ridge;
uniform float shade;
uniform float exposure;
uniform float refraction;
uniform float refraction_width;
uniform float gloss;
uniform float rim_width;
uniform float sheen;
uniform bool glass;
uniform vec3 color_a;
uniform vec3 color_b;
uniform vec3 color_c;
uniform vec3 color_d;

vec3 finishFluid(vec3 color, vec2 p) {
    color=mix(color, vec3(.87,.95,1), shade*.22*smoothstep(.15,1.15,dot(p,vec2(-.32,.78))));
    color*=1.0-shade*.34*smoothstep(-.1,1.2,dot(p,vec2(.45,-.62)));
    color*=1.0-shade*.22*smoothstep(.72,1.08,length(p));
    return clamp(color,0.0,1.0);
}
float auroraLayer(vec2 p, float t, float offset) {
    float drift=t*.18+offset*2.5;
    float wave1=sin(p.x*(2.0+warp*.13)+drift+offset*6.0)*.25;
    float wave2=sin(p.x*3.7+drift*1.3+offset*4.0)*.12;
    float wave3=sin(p.x*7.2+drift*.7+offset*8.0)*.055;
    float n=lqFbm(vec2(p.x*1.6+drift*.35,p.y*.8+offset*3.0),.018).x;
    float center=offset*.46+wave1+wave2+wave3+(n-.5)*.28;
    float dist=abs(p.y-center);
    float glow=exp(-dist*dist*(13.0-5.0*ridge));
    float shimmer=lqFbm(vec2(p.x*4.0+t*.22,p.y*7.0+offset*5.0),.012).x;
    return glow*(.64+.36*shimmer);
}
vec3 auroraFluid(vec2 p, float t) {
    vec2 q=p*(.82+zoom*.58);
    float l0=auroraLayer(q,t,-.72),l1=auroraLayer(q,t,0.0),l2=auroraLayer(q,t,.72);
    vec3 color=color_a*(.46+.18*(q.y+1.0));
    color+=color_b*l0*1.3+color_c*l1*1.15+color_d*l2*1.2;
    color+=mix(color_b,color_d,.5)*min(l0*l2,l1)*.65;
    vec2 starUv=(q+vec2(1))*18.0;
    float starHash=lqHash(floor(starUv));
    vec2 starLocal=fract(starUv)-vec2(.5);
    float stars=step(.965,starHash)*exp(-dot(starLocal,starLocal)*90.0)*
                (.55+.45*sin(t*(1.0+starHash*2.0)+starHash*6.28));
    color+=vec3(.87,.95,1)*stars*(1.0-clamp(l0+l1+l2,0.0,1.0));
    color/=vec3(1)+color*.28;
    return finishFluid(color,p);
}
float refractionProfile(float t) {
    float depth=clamp(t,0.0,1.0);
    return 1.0-sqrt(max(1.0-(1.0-depth)*(1.0-depth),0.0));
}
float highlightLobe(vec2 normal, vec2 direction, float cut, float power) {
    return pow(clamp((dot(normal,direction)-cut)/max(1.0-cut,.001),0.0,1.0),power);
}
vec4 mainImage(vec2 uv01) {
    vec2 fc=vec2(uv01.x,1.0-uv01.y)*u_resolution;
    vec2 uv=(2.0*fc-u_resolution)/max(min(u_resolution.x,u_resolution.y),1.0);
    float rad=max(orb_radius,.05), t=u_time;
    float r=length(uv), aa=max(fwidth(r),.002);
    float coverage=1.0-smoothstep(rad-aa,rad+aa,r);
    if (coverage<=0.0) return vec4(0);
    vec2 p=uv/rad, normal=r>.0001 ? uv/r : vec2(0);
    float pd=length(p), depth=max(1.0-pd,0.0);
    float profile=pow(refractionProfile(depth/max(.015+.95*refraction_width,.001)),.68);
    vec3 fluid=auroraFluid(p,t);
    if (glass) {
        vec2 sampleP=p-normal*1.6*clamp(refraction,0.0,1.0)*profile;
        float split=.14*clamp(gloss,0.0,2.0)*clamp(refraction,0.0,1.0)*profile;
        fluid=vec3(auroraFluid(sampleP-normal*split,t).r,
                   auroraFluid(sampleP,t).g,auroraFluid(sampleP+normal*split,t).b);
        float band=1.0-smoothstep(0.0,.026+.055*rim_width,depth);
        float rim=pow(band,1.8), dispersion=rim*gloss*(.8+.8*rim_width);
        fluid=mix(fluid,vec3(.54,.85,1),clamp(rim*refraction*.45,0.0,1.0));
        fluid=mix(fluid,vec3(.49,.75,1),clamp(dispersion*highlightLobe(normal,normalize(vec2(.84,.54)),-.32,1.8),0.0,1.0));
        fluid=mix(fluid,vec3(1,.65,.85),clamp(dispersion*highlightLobe(normal,normalize(vec2(-.62,-.78)),-.28,2.0),0.0,1.0));
        float key=rim*highlightLobe(normal,normalize(vec2(-.68,.73)),.2,2.8)*sheen*1.4;
        float fill=rim*highlightLobe(normal,normalize(vec2(.74,-.67)),.4,3.6)*sheen;
        fluid=mix(fluid,vec3(.92,.96,1),clamp(key,0.0,1.0));
        fluid=mix(fluid,vec3(1,.91,.96),clamp(fill,0.0,1.0));
    }
    // Saturn uses straight-alpha blending; Orb's original output is premultiplied.
    return vec4(clamp(fluid*max(exposure,0.0),0.0,1.0),coverage);
}
