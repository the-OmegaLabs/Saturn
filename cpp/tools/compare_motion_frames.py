"""Compare fixed-time OpenGL sequences, including per-control and temporal gates."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

MAX_PIXELS = 1 << 24
TIMES = {
    "controls": (0,15,50,75,100,150,200,250,300,330,375,400,449,500,600,850),
    "dialog": (0,30,75,150,225,300,330,375,450,500),
    "snack": (0,30,75,150,225,300,330,375,450,500),
}
REGIONS = {
    "button": (12,12,150,70),
    "checkbox": (10,90,130,150),
    "switch": (182,86,272,148),
    "slider": (4,155,330,223),
    "field": (16,230,330,310),
    "list": (350,16,550,215),
    "menu": (350,230,550,460),
}

def load(path):
    with Image.open(path) as image:
        if image.width*image.height > MAX_PIXELS:
            raise ValueError(f"image exceeds pixel cap: {path}")
        return image.convert("RGB")

def metrics(a,b,tolerance):
    delta = ImageChops.difference(a,b)
    channels = delta.split()
    maximum = ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),channels[2])
    fraction = sum(maximum.histogram()[tolerance+1:])/(a.width*a.height)
    return sum(ImageStat.Stat(delta).mean)/3,fraction

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("python_frames",type=Path)
    parser.add_argument("cpp_frames",type=Path)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--sheet",type=Path)
    args = parser.parse_args()
    report = {"frames":[],"regions":[],"temporal":[],"failures":[]}
    for scene,times in TIMES.items():
        py,cpp = [],[]
        for ms in times:
            name = f"{scene}-{ms}.png"
            a,b = load(args.python_frames/name),load(args.cpp_frames/name)
            if a.size != b.size or a.size != (640,480):
                raise ValueError(f"frame shape mismatch: {name}: {a.size} {b.size}")
            py.append(a); cpp.append(b)
            mean,fraction = metrics(a,b,12)
            report["frames"].append(dict(name=name,mean=mean,difference_fraction=fraction))
            if mean > 2 or fraction > .04:
                report["failures"].append(f"{name}: global mean={mean:.4f}, fraction={fraction:.4f}")
            if scene == "controls":
                for region,(x0,y0,x1,y1) in REGIONS.items():
                    mean,fraction = metrics(a.crop((x0,y0,x1,y1)),b.crop((x0,y0,x1,y1)),12)
                    report["regions"].append(dict(name=name,region=region,mean=mean,difference_fraction=fraction))
                    if mean > 5 or fraction > .12:
                        report["failures"].append(f"{name}/{region}: mean={mean:.4f}, fraction={fraction:.4f}")
        for region,rect in (REGIONS.items() if scene == "controls" else [(scene,(0,0,640,480))]):
            if scene == "controls" and region == "list":
                rect = (522,24,540,204) # scrollbar motion, not the stationary row backgrounds
            x0,y0,x1,y1 = rect
            a = [im.crop((x0,y0,x1,y1)) for im in py]
            b = [im.crop((x0,y0,x1,y1)) for im in cpp]
            # A non-moving/wrongly timed render must not pass on static similarity.
            py_motion = [metrics(a[i],a[i-1],12)[0] for i in range(1,len(a))]
            cpp_motion = [metrics(b[i],b[i-1],12)[0] for i in range(1,len(b))]
            if sum(py_motion) < 1:
                report["failures"].append(f"{scene}/{region}: reference motion coverage is too weak")
            if sum(cpp_motion) < .75*sum(py_motion):
                report["failures"].append(f"{scene}/{region}: candidate lacks expected motion")
            temporal_error = sum(abs(a-b) for a,b in zip(py_motion,cpp_motion))/len(py_motion)
            report["temporal"].append(dict(scene=scene,region=region,python_motion=py_motion,
                cpp_motion=cpp_motion,mean_change_error=temporal_error))
            if temporal_error > 2:
                report["failures"].append(f"{scene}/{region}: temporal error={temporal_error:.4f}")
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    if args.sheet:
        tiles = [("controls",75),("controls",150),("controls",375),("dialog",150),("snack",150)]
        sheet = Image.new("RGB",(640,260*len(tiles)),(18,18,18))
        draw = ImageDraw.Draw(sheet)
        for row,(scene,ms) in enumerate(tiles):
            y = row*260
            draw.text((8,y+3),f"{scene} {ms}ms: Python (left) / C++ (right)",fill="white")
            for column,directory in enumerate((args.python_frames,args.cpp_frames)):
                with Image.open(directory/f"{scene}-{ms}.png") as image:
                    sheet.paste(image.convert("RGB").resize((320,240)),(column*320,y+20))
        sheet.save(args.sheet)
    print(f"{len(report['frames'])} GPU frames, {len(report['regions'])} region comparisons, "
          f"{len(report['temporal'])} temporal comparisons")
    print(f"worst global mean={max(f['mean'] for f in report['frames']):.4f}, "
          f"fraction={max(f['difference_fraction'] for f in report['frames']):.4f}")
    if report["failures"]:
        print("\n".join(report["failures"]))
        raise SystemExit(1)
    print("PASS: fixed-time OpenGL rendering and visible motion are broadly comparable")

if __name__ == "__main__":
    main()
