"""Expressive rounded-polygon loading and moving-wave progress controls."""
import json
import math
import time
from functools import lru_cache
from pathlib import Path

import pygame

from .. import colors, motion
from ..control import Control


@lru_cache(maxsize=1)
def _shapes():
    return json.loads((Path(__file__).parents[1] / '_gen' / 'loading_shapes.json').read_text())


def _morph_points(curves, progress):
    points = []
    p = max(0.0, min(1.0, progress))
    for start, end in curves:
        c = [a + (b - a) * p for a, b in zip(start, end)]
        for i in range(8):
            t = i / 8
            u = 1 - t
            points.append((u**3*c[0] + 3*u*u*t*c[2] + 3*u*t*t*c[4] + t**3*c[6],
                           u**3*c[1] + 3*u*u*t*c[3] + 3*u*t*t*c[5] + t**3*c[7]))
    return points


class LoadingIndicator(Control):
    """Seven rounded polygons morph in a continuous rotating loop.

    ``value=None`` animates SoftBurst, Cookie9Sided, Pentagon, Pill, Sunny,
    Cookie4Sided and Oval. A numeric value morphs from a circle to SoftBurst.
    ``contained=True`` adds a primary-container capsule.
    """
    shape_names = ('SoftBurst', 'Cookie9Sided', 'Pentagon', 'Pill', 'Sunny', 'Cookie4Sided', 'Oval')

    def __init__(self, value=None, *, color=None, bgcolor=None, contained=False, **base):
        super().__init__(**base)
        self.value, self.color, self.bgcolor = value, color, bgcolor
        self.contained = contained
        self._started = time.perf_counter()
        self._elapsed = 0.0

    def _intrinsic(self, max_w, max_h, scale):
        return self._width if self._width is not None else 48, self._height if self._height is not None else 48

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _geometry(self):
        data = _shapes()
        if self.value is not None:
            progress = max(0.0, min(1.0, float(self.value)))
            return _morph_points(data['determinate'], progress), progress * math.pi, 1.0
        index = int(self._elapsed / .65)
        t = self._elapsed % .65
        omega, damping = math.sqrt(200), .6
        wd = omega * math.sqrt(1 - damping*damping)
        progress = 1 - math.exp(-damping*omega*t) * (
            math.cos(wd*t) + damping/math.sqrt(1-damping*damping)*math.sin(wd*t))
        if t > .6:
            progress = 1.0
        angle = (1 + index + progress) * math.pi/2 + self._elapsed/4.666 * math.tau
        return _morph_points(data['sequence'][index % 7], progress), angle, 1 + max(0, progress-1)*.15

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        if w <= 0 or h <= 0:
            return
        if self.contained or self.bgcolor is not None:
            r.fill_rect(x, y, w, h, colors.parse_color(self.bgcolor or colors.Colors.PRIMARY_CONTAINER),
                        radius=min(w, h)/2)
        points, angle, bounce = self._geometry()
        cx = (min(p[0] for p in points) + max(p[0] for p in points))/2
        cy = (min(p[1] for p in points) + max(p[1] for p in points))/2
        scale = min(w, h) * r.scale * (38/48) * _shapes()['scale'] * bounce
        c, s = math.cos(angle), math.sin(angle)
        pw, ph = max(1, round(w*r.scale)), max(1, round(h*r.scale))
        vertices = [(pw/2 + ((px-cx)*c-(py-cy)*s)*scale,
                     ph/2 + ((px-cx)*s+(py-cy)*c)*scale) for px, py in points]
        surface = pygame.Surface((pw, ph), pygame.SRCALPHA)
        role = colors.Colors.ON_PRIMARY_CONTAINER if self.contained else colors.Colors.PRIMARY
        pygame.draw.polygon(surface, colors.parse_color(self.color or role), vertices)
        r.blit(surface, x, y)

    def _tick_animations(self, now):
        active = super()._tick_animations(now)
        if self.visible and self.value is None:
            self._elapsed = max(0.0, now-self._started)
            return True
        return active


def _line(surface, points, color, width):
    if len(points) < 2:
        return
    pygame.draw.lines(surface, color, False, points, max(1, round(width)))
    for p in (points[0], points[-1]):
        pygame.draw.circle(surface, color, p, max(1, round(width/2)))


class WavyProgressIndicator(Control):
    """Linear moving-wave progress. ``value=None`` shows indefinite progress."""
    circular = False

    def __init__(self, value=None, *, color=None, bgcolor=None, stroke_width=4,
                 amplitude=None, wavelength=None, wave_speed=1.0, **base):
        super().__init__(**base)
        if stroke_width <= 0 or (wavelength is not None and wavelength <= 0):
            raise ValueError('stroke_width and wavelength must be positive')
        self.value, self.color, self.bgcolor = value, color, bgcolor
        self.stroke_width = float(stroke_width)
        self.amplitude = (1.6 if self.circular else 3.0) if amplitude is None else max(0, amplitude)
        self.wavelength = wavelength
        self.wave_speed = wave_speed
        self._started = time.perf_counter()
        self._elapsed = 0.0
        self._last_value = value
        self._display_value = float(value or 0)

    def _intrinsic(self, max_w, max_h, scale):
        w, h = (48, 48) if self.circular else (240, 10)
        return self._width if self._width is not None else w, self._height if self._height is not None else h

    def _place(self, x, y, w, h, scale):
        self._rect = x, y, w, h

    def _prepare_animations(self, now):
        super()._prepare_animations(now)
        if self.value != self._last_value:
            self._last_value = self.value
            if self.value is not None:
                self._animate_internal('_display_value', max(0, min(1, float(self.value))),
                                       motion.MEDIUM1, motion.STANDARD, now=now)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        if w <= 0 or h <= 0:
            return
        scale = r.scale
        surface = pygame.Surface((max(1, round(w*scale)), max(1, round(h*scale))), pygame.SRCALPHA)
        active = colors.parse_color(self.color or colors.Colors.PRIMARY)
        track = colors.parse_color(self.bgcolor or colors.Colors.SECONDARY_CONTAINER)
        progress = max(0, min(1, self._display_value))
        amplitude = self.amplitude
        if self.value is not None:
            amplitude *= max(0, min(1, (progress-.1)/.1, (.95-progress)/.1))
        wavelength = self.wavelength or (15 if self.circular else 20 if self.value is None else 40)
        phase = self._elapsed * self.wave_speed * math.tau
        stroke = self.stroke_width
        if self.circular:
            radius = max(0, min(w, h)/2 - stroke/2 - self.amplitude)
            if radius <= 0:
                return
            start = -math.pi/2
            sweep = progress * math.tau
            if self.value is None:
                start += self._elapsed * 2.0
                sweep = math.radians(150 + 120*math.sin(self._elapsed*2.5))
            gap = min(sweep/2, (4+stroke)/radius)
            def arc(a, b, wave, color):
                if b <= a:
                    return
                n = max(2, math.ceil((b-a)*radius*scale))
                waves = max(1, round(math.tau*radius/wavelength))
                points = []
                for i in range(n+1):
                    theta = a+(b-a)*i/n
                    rr = radius + wave*math.sin(theta*waves-phase)
                    points.append(((w/2+math.cos(theta)*rr)*scale,
                                   (h/2+math.sin(theta)*rr)*scale))
                _line(surface, points, color, stroke*scale)
            if sweep < math.tau:
                arc(start+sweep+gap, start+math.tau-gap, 0, track)
            if sweep > 0:
                arc(start, start+sweep, amplitude, active)
        else:
            left, right = stroke/2, max(stroke/2, w-stroke/2)
            length = right-left
            a, b = left, left+length*progress
            if self.value is None:
                p = (self._elapsed/1.8) % 1.4 - .4
                a, b = left+length*max(0, p), left+length*min(1, p+.4)
            def straight(a, b):
                if b > a:
                    _line(surface, [(a*scale,h*scale/2),(b*scale,h*scale/2)], track, stroke*scale)
            straight(left, a-4-stroke)
            straight(b+(4+stroke if b>a else 0), right)
            if b > a:
                n = max(2, math.ceil((b-a)*scale))
                points = []
                for i in range(n+1):
                    px = a+(b-a)*i/n
                    taper = min(1, (px-a)/(wavelength/4), (b-px)/(wavelength/4))
                    py = h/2 + amplitude*taper*math.sin(px/wavelength*math.tau-phase)
                    points.append((px*scale,py*scale))
                _line(surface, points, active, stroke*scale)
            if self.value is not None:
                pygame.draw.circle(surface, active, (round(right*scale),round(h*scale/2)), max(1,round(2*scale)))
        r.blit(surface, x, y)

    def _tick_animations(self, now):
        active = super()._tick_animations(now)
        if self.visible and (self.value is None or 0 < self._display_value < 1):
            self._elapsed = max(0, now-self._started)
            return True
        return active


class LinearWavyProgressIndicator(WavyProgressIndicator):
    pass


class CircularWavyProgressIndicator(WavyProgressIndicator):
    circular = True
