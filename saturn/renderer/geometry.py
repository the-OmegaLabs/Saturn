"""Small triangle meshes with interpolated edge coverage, including at 1x.

Only geometry is constructed on the CPU; the backends rasterize and blend it.
Coverage bands are measured in logical pixels so they stay one device pixel.
"""
import math


def _quad(points, coverage, a, b, c, d, aa=1, ba=1, ca=1, da=1):
    points.extend((a, b, c, a, c, d))
    coverage.extend((aa, ba, ca, aa, ca, da))


def stroke_triangles(vertices, width, fringe, *, closed=False):
    """Mitered stroke strip; round endpoint caps are supplied by the renderer."""
    vertices = list(vertices)
    vertices = [point for i, point in enumerate(vertices)
                if i == 0 or point != vertices[i - 1]]
    if len(vertices) < 2 or width <= 0:
        return [], []
    if closed and vertices[-1] == vertices[0]:
        vertices.pop()
    count = len(vertices)
    normals = []
    for i in range(count if closed else count - 1):
        x0, y0 = vertices[i]
        x1, y1 = vertices[(i + 1) % count]
        length = math.hypot(x1 - x0, y1 - y0)
        normals.append((-(y1 - y0) / length, (x1 - x0) / length))
    offsets = []
    for i in range(count):
        if not closed and i == 0:
            offsets.append(normals[0])
        elif not closed and i == count - 1:
            offsets.append(normals[-1])
        else:
            ax, ay = normals[i - 1]
            bx, by = normals[i % len(normals)]
            # Clamp sharp miters instead of sending a huge spike offscreen.
            denominator = max(.25, 1 + ax * bx + ay * by)
            offsets.append(((ax + bx) / denominator,
                            (ay + by) / denominator))
    inside = max(0, (width - fringe) / 2)
    outside = (width + fringe) / 2
    opacity = min(1, width / fringe) if fringe else 1
    rings = []
    for distance in (-outside, -inside, inside, outside):
        rings.append([(x + nx * distance, y + ny * distance)
                      for (x, y), (nx, ny) in zip(vertices, offsets)])
    points, coverage = [], []
    for i in range(count if closed else count - 1):
        j = (i + 1) % count
        for ring, (alpha0, alpha1) in enumerate(
                ((0, opacity), (opacity, opacity), (opacity, 0))):
            _quad(points, coverage, rings[ring][i], rings[ring][j],
                  rings[ring + 1][j], rings[ring + 1][i],
                  alpha0, alpha0, alpha1, alpha1)
    if fringe and not closed:
        for index, normal, sign in ((0, normals[0], -1),
                                    (count - 1, normals[-1], 1)):
            dx, dy = normal[1] * fringe * sign, -normal[0] * fringe * sign
            for ring, (alpha0, alpha1) in enumerate(
                    ((0, opacity), (opacity, opacity), (opacity, 0))):
                a, b = rings[ring][index], rings[ring + 1][index]
                _quad(points, coverage, a, (a[0] + dx, a[1] + dy),
                      (b[0] + dx, b[1] + dy), b, alpha0, 0, 0, alpha1)
    return points, coverage


def polygon_triangles(vertices, fringe, center):
    """Fill a polygon visible from its center, plus an outer coverage band.

    Expressive loading shapes are radial polygons. A center fan avoids general
    path tessellation and preserves their concave scallops during morphing.
    """
    vertices = list(vertices)
    if len(vertices) < 3:
        return [], []
    points, coverage = [], []
    count = len(vertices)
    area = sum(vertices[i][0] * vertices[(i + 1) % count][1] -
               vertices[(i + 1) % count][0] * vertices[i][1]
               for i in range(count))
    direction = 1 if area >= 0 else -1
    normals = []
    for i in range(count):
        x, y = vertices[i]
        ex, ey = vertices[(i + 1) % count]
        length = math.hypot(ex - x, ey - y)
        normals.append((direction * (ey - y) / max(length, .0001),
                        -direction * (ex - x) / max(length, .0001)))
    outer = []
    for i, (x, y) in enumerate(vertices):
        ax, ay = normals[i - 1]
        bx, by = normals[i]
        factor = fringe / max(.25, 1 + ax * bx + ay * by)
        outer.append((x + (ax + bx) * factor, y + (ay + by) * factor))
    for i in range(count):
        j = (i + 1) % count
        points.extend((center, vertices[i], vertices[j]))
        coverage.extend((1, 1, 1))
        if fringe:
            _quad(points, coverage, vertices[i], outer[i], outer[j], vertices[j],
                  1, 0, 0, 1)
    return points, coverage


def arc_triangles(x, y, radius, start, end, width, fringe):
    """Annular sector with coverage on both radii and the two butt caps."""
    if radius <= 0 or width <= 0 or end <= start:
        return [], []
    sweep = min(math.tau, end - start)
    closed = sweep >= math.tau - .000001
    inner = max(0, radius - width)
    # Bound chord error, independent of DPI, instead of visible coarse facets.
    tolerance = max(fringe, .5) * .15
    angle_step = 2 * math.acos(max(-1, 1 - tolerance / radius))
    segments = max(8, math.ceil(sweep / max(.005, angle_step)))
    angles = [start + sweep * i / segments for i in range(segments + 1)]
    angle_coverage = [1] * len(angles)
    if fringe and not closed:
        cap_angle = fringe / (2 * max(radius - width / 2, fringe))
        angles = [start - cap_angle, start + cap_angle] + angles[1:-1] + [
            start + sweep - cap_angle, start + sweep + cap_angle]
        # Tiny sectors can have overlapping cap bands. Keep their samples
        # ordered and let the longitudinal coverage taper to zero.
        angles = sorted(set(angles))
        angle_coverage = [max(0, min(1, (a - start + cap_angle) / (2 * cap_angle),
                                      (start + sweep + cap_angle - a) / (2 * cap_angle)))
                          for a in angles]
    radial = [(0, 1)] if inner == 0 else [
        (max(0, inner - fringe / 2), 0), (inner + fringe / 2, 1)]
    radial.extend(((max(inner, radius - fringe / 2), 1),
                   (radius + fringe / 2, 0 if fringe else 1)))
    radial.sort()
    points, coverage = [], []
    for ring in range(len(radial) - 1):
        r0, alpha0 = radial[ring]
        r1, alpha1 = radial[ring + 1]
        if r1 <= r0:
            continue
        for i in range(len(angles) - 1):
            a0, a1 = angles[i:i + 2]
            p0 = (x + math.cos(a0) * r0, y + math.sin(a0) * r0)
            p1 = (x + math.cos(a1) * r0, y + math.sin(a1) * r0)
            p2 = (x + math.cos(a1) * r1, y + math.sin(a1) * r1)
            p3 = (x + math.cos(a0) * r1, y + math.sin(a0) * r1)
            c0, c1 = angle_coverage[i:i + 2]
            _quad(points, coverage, p0, p1, p2, p3,
                  alpha0 * c0, alpha0 * c1, alpha1 * c1, alpha1 * c0)
    return points, coverage
