"""Run all 13 MIT-licensed Orb GLSL presets with a native settings window."""
if __package__:
    from .orb_catalog import build, orb_uniforms, PRESETS, apply_preset, run_orb
else:
    from orb_catalog import build, orb_uniforms, PRESETS, apply_preset, run_orb

if __name__ == '__main__':
    run_orb(build, 'All 13 Orb GLSL presets', ('home', 'editor'))
