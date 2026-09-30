#!/usr/bin/env python3
"""Show the live song's arrangement on a ProPresenter stage screen.

Polls the ProPresenter API once a second and writes the arrangement name to a
text file. A stage layout text box linked to that file shows it live. The file
is only rewritten when the text changes.

What gets written:
  - Playlist song live, arrangement picked      -> the arrangement name
  - Playlist song live, no arrangement picked   -> "Default"
  - Non-song presentation live (sermon, etc.)   -> blank
  - Nothing live, or triggered from the library -> blank

Works on macOS and Windows. Logs to arrangement-watch.log next to the output
file. Set PROPRESENTER_PORT to skip automatic port detection.

Usage: arrangement_watch.py [output_file]
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

OUT = os.path.expanduser(
    sys.argv[1] if len(sys.argv) > 1 else "~/ProPresenter Stage Text/arrangement.txt")
LOG = os.path.join(os.path.dirname(OUT), "arrangement-watch.log")
WINDOWS = sys.platform == "win32"
DEFAULT_TEXT = "Default"
BLANK_TEXT = ""
POLL_SECONDS = 1

# The API has no "is this a song" flag, so a presentation counts as a song if
# any of its groups has a song-section name.
SONG_GROUP = re.compile(
    r"^\s*(verse|chorus|pre[\s-]?chorus|bridge|tag|intro|outro|ending|refrain|"
    r"vamp|interlude|turnaround|instrumental|solo)\b", re.I)


def log(msg):
    # %-I (no leading zero) doesn't exist on Windows, so strip the zero by hand.
    stamp = time.strftime("%Y-%m-%d %I:%M:%S %p").replace(" 0", " ", 1)
    line = f"{stamp} {msg}"
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    if sys.stdout:  # pythonw on Windows has no console
        print(line, flush=True)


def run(cmd):
    kw = {"creationflags": 0x08000000} if WINDOWS else {}  # CREATE_NO_WINDOW
    return subprocess.run(cmd, capture_output=True, text=True, **kw).stdout


def mac_ports(lsof_out):
    return [m.group(1) for line in lsof_out.splitlines() if line.startswith("ProPresen")
            for m in [re.search(r":(\d+) \(LISTEN\)", line)] if m]


def windows_ports(tasklist_out, netstat_out):
    pids = {row[1] for row in (l.strip('"').split('","') for l in tasklist_out.splitlines())
            if len(row) > 1 and row[0].lower().startswith("propresenter")}
    ports = []
    for line in netstat_out.splitlines():
        parts = line.split()
        # A listening socket has no remote end (0.0.0.0:0 / [::]:0). Checking that
        # instead of the word "LISTENING" works on non-English Windows too.
        if (len(parts) == 5 and parts[0] == "TCP" and parts[2] in ("0.0.0.0:0", "[::]:0")
                and parts[4] in pids):
            ports.append(parts[1].rsplit(":", 1)[1])
    return ports


def candidate_ports():
    if os.environ.get("PROPRESENTER_PORT"):
        return [os.environ["PROPRESENTER_PORT"]]
    if WINDOWS:
        return windows_ports(run(["tasklist", "/FO", "CSV", "/NH"]),
                             run(["netstat", "-ano", "-p", "TCP"]))
    return mac_ports(run(["/usr/sbin/lsof", "-nP", "-iTCP", "-sTCP:LISTEN"]))


def find_port():
    """ProPresenter's API port isn't fixed, so find it by asking each port
    ProPresenter is listening on for /version."""
    for port in dict.fromkeys(candidate_ports()):
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/version", timeout=1) as r:
                if "api_version" in r.read().decode():
                    return port
        except Exception:
            pass
    return None


def get(port, path):
    with urllib.request.urlopen(f"http://localhost:{port}{path}", timeout=2) as r:
        return json.load(r)


_names = {}    # arrangement_uuid -> name
_is_song = {}  # presentation_uuid -> bool


def arrangement_name(port, active):
    """/v1/playlist/active returns arrangement_name "" even when an arrangement
    is picked (ProPresenter 21.4); only arrangement_uuid is filled in. The full
    playlist does include the name, so look it up there."""
    info = active["playlist_item"]["presentation_info"]
    name = (info.get("arrangement_name") or "").strip()
    uuid = info.get("arrangement_uuid") or ""
    if name or not uuid:
        return name
    if uuid not in _names:
        pl = get(port, f"/v1/playlist/{active['playlist']['uuid']}")
        for it in pl.get("items", []):
            pi = it.get("presentation_info") or {}
            if pi.get("arrangement_uuid"):
                _names[pi["arrangement_uuid"]] = (pi.get("arrangement_name") or "").strip()
    return _names.get(uuid, "")


def is_song(port, pres_uuid):
    if pres_uuid not in _is_song:
        groups = get(port, f"/v1/presentation/{pres_uuid}")["presentation"].get("groups", [])
        _is_song[pres_uuid] = any(SONG_GROUP.match(g.get("name") or "") for g in groups)
    return _is_song[pres_uuid]


def current_text(port):
    live = (get(port, "/v1/presentation/active") or {}).get("presentation")
    active = get(port, "/v1/playlist/active").get("presentation") or {}
    item = active.get("playlist_item")
    live_uuid = (live or {}).get("id", {}).get("uuid")
    # Only trust the playlist item if it's what's actually live. If it isn't,
    # the presentation was triggered from the library and we can't know the
    # arrangement.
    if (live_uuid and item and item.get("type") == "presentation"
            and (item.get("presentation_info") or {}).get("presentation_uuid") == live_uuid):
        text = arrangement_name(port, active)
        if not text:
            text = DEFAULT_TEXT if is_song(port, live_uuid) else BLANK_TEXT
        return text, item["id"]["name"]
    return BLANK_TEXT, (live or {}).get("id", {}).get("name")


def write(text):
    # Overwrite the same file in place. Replacing it with a new file (the usual
    # "atomic write") can break ProPresenter's link to it.
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    log(f"writing to {OUT}")
    port, last, waiting = None, None, False
    while True:
        if not port:
            try:
                port = find_port()
            except Exception as e:
                log(f"port lookup failed ({e})")
            if not port:
                if not waiting:
                    log("waiting for ProPresenter")
                    waiting = True
                time.sleep(5)
                continue
            waiting = False
            _names.clear()
            _is_song.clear()
            log(f"ProPresenter API on port {port}")
        try:
            text, song = current_text(port)
        except Exception as e:
            log(f"lost ProPresenter ({e}); looking for it again")
            port = None
            time.sleep(POLL_SECONDS)
            continue
        if text != last:
            try:
                write(text)
            except OSError as e:
                # Windows can refuse the write while ProPresenter has the file
                # open. Leave `last` alone so the next check tries again.
                log(f"couldn't write {OUT} ({e}); retrying")
            else:
                log(f"live: {song!r} -> wrote {text!r}")
                last = text
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
