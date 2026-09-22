"""Material Web motion tokens used by Saturn's built-in controls."""

# Durations from md.sys.motion.
SHORT1 = 50
SHORT2 = 100
SHORT3 = 150
SHORT4 = 200
MEDIUM1 = 250
MEDIUM2 = 300
MEDIUM3 = 350
MEDIUM4 = 400
LONG1 = 450
LONG2 = 500

# Private curve names are resolved by ``animation.ease``. Keeping them out of
# AnimationCurve preserves Flet's public enum while matching Material Web's
# exact cubic-bezier values.
STANDARD = "materialStandard"
STANDARD_ACCELERATE = "materialStandardAccelerate"
STANDARD_DECELERATE = "materialStandardDecelerate"
EMPHASIZED = "materialEmphasized"
EMPHASIZED_ACCELERATE = "materialEmphasizedAccelerate"
EMPHASIZED_DECELERATE = "materialEmphasizedDecelerate"
SWITCH_OVERSHOOT = "materialSwitchOvershoot"
PROGRESS = "materialProgress"
