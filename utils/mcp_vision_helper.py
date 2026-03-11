import argparse
import base64
import json
import os
import subprocess
import tempfile

import cv2


def _run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "command failed").strip())
    return p.stdout.strip()


def _adb_args(device=None):
    return ["-s", device] if device else []


def capture_screen(device=None):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.close()
    remote = "/sdcard/taskex_mcp_screen.png"
    _run(["adb", *_adb_args(device), "shell", "screencap", "-p", remote])
    _run(["adb", *_adb_args(device), "pull", remote, tmp.name])
    return tmp.name


def template_match(device, template_path, threshold):
    if not os.path.exists(template_path):
        return {"ok": False, "error": f"Template not found: {template_path}"}

    shot_path = capture_screen(device)
    try:
        src = cv2.imread(shot_path)
        tpl = cv2.imread(template_path)
        if src is None:
            return {"ok": False, "error": "Failed to read screenshot"}
        if tpl is None:
            return {"ok": False, "error": "Failed to read template"}

        result = cv2.matchTemplate(src, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < threshold:
            return {
                "ok": True,
                "matched": False,
                "score": float(max_val),
                "threshold": float(threshold),
            }

        h, w = tpl.shape[:2]
        x = int(max_loc[0] + w / 2)
        y = int(max_loc[1] + h / 2)
        return {
            "ok": True,
            "matched": True,
            "score": float(max_val),
            "threshold": float(threshold),
            "x": x,
            "y": y,
            "width": int(w),
            "height": int(h),
        }
    finally:
        try:
            os.remove(shot_path)
        except Exception:
            pass


def screen_region(device, x1, y1, x2, y2, output_path=None):
    shot_path = capture_screen(device)
    try:
        src = cv2.imread(shot_path)
        if src is None:
            return {"ok": False, "error": "Failed to read screenshot"}

        h, w = src.shape[:2]
        x1 = max(0, min(int(x1), w - 1))
        y1 = max(0, min(int(y1), h - 1))
        x2 = max(1, min(int(x2), w))
        y2 = max(1, min(int(y2), h))
        if x2 <= x1 or y2 <= y1:
            return {"ok": False, "error": "Invalid region"}

        region = src[y1:y2, x1:x2]

        if output_path:
            cv2.imwrite(output_path, region)
            return {
                "ok": True,
                "saved": True,
                "output": output_path,
                "width": int(x2 - x1),
                "height": int(y2 - y1),
            }

        ok, encoded = cv2.imencode(".png", region)
        if not ok:
            return {"ok": False, "error": "Failed to encode region"}
        return {
            "ok": True,
            "saved": False,
            "pngBase64": base64.b64encode(encoded.tobytes()).decode("ascii"),
            "encoding": "base64",
            "width": int(x2 - x1),
            "height": int(y2 - y1),
        }
    finally:
        try:
            os.remove(shot_path)
        except Exception:
            pass


def find_and_tap(device, template_path, threshold):
    res = template_match(device, template_path, threshold)
    if not res.get("ok") or not res.get("matched"):
        return res

    _run(["adb", *_adb_args(device), "shell", "input", "tap", str(res["x"]), str(res["y"])])
    res["tapped"] = True
    return res


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_match = sub.add_parser("template-match")
    p_match.add_argument("--template", required=True)
    p_match.add_argument("--threshold", type=float, default=0.85)
    p_match.add_argument("--device", default=None)

    p_region = sub.add_parser("screen-region")
    p_region.add_argument("--x1", type=int, required=True)
    p_region.add_argument("--y1", type=int, required=True)
    p_region.add_argument("--x2", type=int, required=True)
    p_region.add_argument("--y2", type=int, required=True)
    p_region.add_argument("--output", default=None)
    p_region.add_argument("--device", default=None)

    p_tap = sub.add_parser("find-and-tap")
    p_tap.add_argument("--template", required=True)
    p_tap.add_argument("--threshold", type=float, default=0.85)
    p_tap.add_argument("--device", default=None)

    args = parser.parse_args()

    try:
        if args.command == "template-match":
            out = template_match(args.device, args.template, args.threshold)
        elif args.command == "screen-region":
            out = screen_region(args.device, args.x1, args.y1, args.x2, args.y2, args.output)
        else:
            out = find_and_tap(args.device, args.template, args.threshold)
    except Exception as e:
        out = {"ok": False, "error": str(e)}

    print(json.dumps(out))


if __name__ == "__main__":
    main()
