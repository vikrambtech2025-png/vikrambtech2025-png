#!/usr/bin/env python3
# Animated GIF generator: rolling heatmap, stats flipbook, terminal boot.
# Rendered frame-by-frame with Pillow - no GIF services, no third parties.
# Stats come from docs/data.json (written earlier in the same workflow run);
# the heatmap reads the public contribution calendar directly.
#
# Output goes to assets/generated/ and is mirrored into docs/assets/.
# Byte-identical output is skipped, so data-independent art causes no churn.
import json
import os
import shutil
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_art as g

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow missing - skipping GIF generation", file=sys.stderr)
    sys.exit(0)

BG = (4, 7, 13)
CYAN = (0, 229, 255)
GREEN = (34, 197, 94)
CRIMSON = (255, 31, 75)
GOLD = (255, 179, 0)
VIOLET = (139, 92, 246)
LIGHT = (220, 233, 247)
MUTED = (90, 107, 133)
DOT_OFF = (30, 40, 55)
HEAT = [(14, 20, 32), (19, 68, 58), (34, 125, 85), (55, 181, 110), (126, 255, 169)]

FONT_CANDIDATES = [r"C:\Windows\Fonts\consola.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                   r"C:\Windows\Fonts\cour.ttf",
                   "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]
FONT_BOLD_CANDIDATES = [r"C:\Windows\Fonts\consolab.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                        r"C:\Windows\Fonts\courbd.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"]


def font(size, bold=False):
    for p in (FONT_BOLD_CANDIDATES if bold else FONT_CANDIDATES):
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def write_gif(name, frames, durations, colors=48, pal_frames=None):
    path = os.path.join("assets", "generated", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    # Palette comes from the representative frames only (pal_frames), so a long
    # animation of mostly-empty background can't starve the text colors out.
    src = pal_frames if pal_frames else frames
    w, h = frames[0].size
    mosaic = Image.new("RGB", (w, h * len(src)))
    for i, f in enumerate(src):
        mosaic.paste(f.convert("RGB"), (0, i * h))
    pal = mosaic.quantize(colors=colors)
    conv = [f.convert("RGB").quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    conv[0].save(tmp, format="GIF", save_all=True, append_images=conv[1:], duration=durations,
                 loop=0, optimize=True, disposal=2)
    with open(tmp, "rb") as fh:
        new = fh.read()
    os.remove(tmp)
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            if fh.read() == new:
                print("unchanged", name)
                return
    with open(path, "wb") as fh:
        fh.write(new)
    print("wrote", path, len(new), "bytes,", len(frames), "frames")
    shutil.copyfile(path, os.path.join("docs", "assets", name))


# ----------------------------------------------------------------- heatmap
def build_heatmap(contrib, frames_n=16, span=56):
    if not contrib:
        print("  ! no contribution data - skipping heatmap")
        return
    W, H = 460, 176
    cell, gap = 14, 3
    gx, gy = 26, 44
    end = datetime.strptime(max(contrib), "%Y-%m-%d").date()
    _, longest, cur = g.streaks(contrib)
    f_title = font(11, bold=True)
    f_small = font(9)
    f_label = font(8)
    f_big = font(22, bold=True)
    frames, durs = [], []
    for fr in range(frames_n):
        win_end = end - timedelta(days=frames_n - 1 - fr)
        img = Image.new("RGB", (W, H), BG)
        dr = ImageDraw.Draw(img)
        dr.text((14, 14), "ROLLING HEATMAP // 56 DAYS", font=f_title, fill=CYAN)
        dtag = win_end.isoformat()
        dr.text((W - 14 - dr.textlength(dtag, font=f_small), 15), dtag, font=f_small, fill=MUTED)
        total = 0
        for i in range(span):
            d = win_end - timedelta(days=span - 1 - i)
            lvl, cnt = contrib.get(d.isoformat(), (0, 0))
            total += cnt
            x = gx + (i // 7) * (cell + gap)
            y = gy + ((d.weekday() + 1) % 7) * (cell + gap)
            dr.rectangle([x, y, x + cell - 1, y + cell - 1], fill=HEAT[lvl])
        for r, lab in enumerate("SMTWTFS"):
            dr.text((12, gy + r * (cell + gap) + 2), lab, font=f_label, fill=MUTED)
        px = gx + (span // 7) * (cell + gap) + 22
        dr.text((px, gy + 4), str(total), font=f_big, fill=GREEN)
        dr.text((px, gy + 36), "CONTRIBUTIONS", font=f_label, fill=MUTED)
        dr.text((px, gy + 52), "streak %dd - best %dd" % (cur, longest), font=f_small, fill=LIGHT)
        start = win_end - timedelta(days=span - 1)
        dr.text((px, gy + 72), start.isoformat(), font=f_label, fill=MUTED)
        dr.text((px, gy + 84), "rolling window", font=f_label, fill=MUTED)
        frames.append(img)
        durs.append(130)
    write_gif("heatmap-rolling.gif", frames, durs)


# --------------------------------------------------------------- flipbook
def build_flipbook(data):
    stats = data.get("stats", {})
    langs = data.get("languages", [])
    top = langs[0]["name"] if langs else "-"
    W, H = 400, 160
    panels = [
        ("CONTRIBUTIONS", str(stats.get("contributions", 0)), "this year", GREEN),
        ("LONGEST STREAK", "%d days" % stats.get("longest_streak", 0), "best run", GOLD),
        ("CURRENT STREAK", "%d days" % stats.get("current_streak", 0), "still going", CRIMSON),
        ("PUBLIC REPOS", str(stats.get("repos", 0)), "shipping in public", VIOLET),
        ("TOP LANGUAGE", top, "by real bytes", CYAN),
        ("MISSION", "idealistic ai agents", "for real-world problems", CYAN),
    ]
    f_label = font(11, bold=True)
    f_value = font(19, bold=True)
    f_small = font(10)

    def panel(label, value, sub, col, idx):
        img = Image.new("RGB", (W, H), BG)
        dr = ImageDraw.Draw(img)
        dr.rectangle([10, 10, W - 11, H - 11], outline=col)
        dr.text((26, 32), label, font=f_label, fill=col)
        dr.text((26, 66), value, font=f_value, fill=LIGHT)
        dr.text((26, 106), sub, font=f_small, fill=MUTED)
        for j in range(len(panels)):
            x = 26 + j * 11
            dr.rectangle([x, H - 30, x + 7, H - 24],
                         fill=col if j == idx else DOT_OFF)
        return img

    rendered = [panel(*p, i) for i, p in enumerate(panels)]
    frames, durs = [], []
    for i, img in enumerate(rendered):
        for _ in range(3):
            frames.append(img)
            durs.append(95)
        if i + 1 < len(rendered):
            for a in (0.35, 0.7):
                frames.append(Image.blend(img, rendered[i + 1], a))
                durs.append(45)
    write_gif("stats-flipbook.gif", frames, durs)


# -------------------------------------------------------------------- boot
def build_boot():
    W, H = 460, 186
    lines = [
        ("$ gh profile init vikrambtech2025-png", CYAN),
        ("[ok] obsidian core ........ loaded", GREEN),
        ("[ok] agent runtime ........ idealistic", GREEN),
        ("[ok] rag + colpali + vision  online", GREEN),
        ("$ cat mission.txt", CYAN),
        ("i love to create ai idealistic agents", LIGHT),
        ("that solves real world problem", LIGHT),
        ("$ ", CYAN),
    ]
    typed = {0, 4, 5, 6, 7}
    f = font(12)
    shown = [0] * len(lines)
    cursor_on = [True]

    def render():
        img = Image.new("RGB", (W, H), BG)
        dr = ImageDraw.Draw(img)
        y = 14
        last = None
        for i, (txt, col) in enumerate(lines):
            if shown[i]:
                dr.text((14, y), txt[:shown[i]], font=f, fill=col)
                last = (y, 14 + dr.textlength(txt[:shown[i]], font=f))
            y += 22
        if last is not None and cursor_on[0]:
            dr.rectangle([last[1] + 2, last[0] - 1, last[1] + 10, last[0] + 13], fill=GREEN)
        return img

    frames, durs = [], []
    for i, (txt, _) in enumerate(lines):
        if i in typed:
            for n in range(3, len(txt) + 1, 3):
                shown[i] = n
                frames.append(render())
                durs.append(48)
            shown[i] = len(txt)
        else:
            shown[i] = len(txt)
        frames.append(render())
        durs.append(150 if i not in typed else 60)
    for _ in range(5):
        cursor_on[0] = not cursor_on[0]
        frames.append(render())
        durs.append(520)
    # palette from a few frames that between them contain every text color
    write_gif("boot-terminal.gif", frames, durs, colors=32, pal_frames=frames[:1] + frames[24:25] + frames[34:35] + frames[-1:])


# -------------------------------------------------------------------- main
def main():
    contrib = g.fetch_contributions()
    data = {}
    try:
        with open(os.path.join("docs", "data.json"), encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        print("  ! data.json unavailable:", str(exc)[:70], file=sys.stderr)
    build_heatmap(contrib)
    if data:
        build_flipbook(data)
    else:
        print("  ! skipping flipbook (no stats)")
    build_boot()
    print("gifs done")


if __name__ == "__main__":
    main()
