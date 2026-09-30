# ProPresenter Stage Arrangement

Shows the live song's arrangement name (e.g. "Chorus Only", "1,2,4") on a ProPresenter stage screen, so the band always knows which arrangement is running.

ProPresenter has no stage object for this. This script reads the arrangement from the ProPresenter API and writes it to a text file. A stage layout text box linked to that file updates live.

Works on **macOS** and **Windows**. Tested live with ProPresenter 21.4 on macOS. The Windows version is written but hasn't been tested on a Windows machine yet. If you try it, please open an issue with how it went.

## What the stage box shows

| What's live | Shows |
|---|---|
| Playlist song with an arrangement picked | The arrangement name |
| Playlist song with no arrangement picked | `Default` |
| Sermon, scripture, or any other non-song presentation | blank |
| Nothing live, or a song triggered from the library | blank |

A presentation counts as a **song** if any of its groups is named Verse, Chorus, Pre-Chorus, Bridge, Tag, Intro, Outro, Ending, Refrain, Vamp, Interlude, Turnaround, Instrumental or Solo. The API can't tell songs from other presentations, so the script goes by group names. If a non-song deck uses those group names (e.g. an announcements deck with "Verse 1"), it will show `Default`. Rename that deck's groups to fix it.

Songs triggered straight from the **library** show blank, because the API only reports arrangements for playlist items.

## Setup (macOS)

1. **Enable the API:** in ProPresenter, go to Settings → Network and turn on Network. You don't need to note the port. The script finds it on its own.
2. **Install the watcher:**
   ```bash
   cd "path/to/this/folder"
   bash install.sh
   ```
   This installs a background service that starts at login and restarts the script if it crashes. By default it writes to `~/ProPresenter Stage Text/arrangement.txt`. To use a different file, pass it as an argument: `bash install.sh "/path/to/file.txt"`.

   The service runs the script from wherever this folder is, so keep the folder in place after installing. If you move it, run `bash install.sh` again.
3. **Link the stage text box:** in your stage layout, add a text box and link its text to that file.

To remove it: `bash uninstall.sh`

To run it by hand without installing: `python3 arrangement_watch.py [output_file]`

## Setup (Windows)

1. **Enable the API:** in ProPresenter, go to Settings → Network and turn on Network.
2. **Install Python:** Windows doesn't include it. Download it from [python.org](https://www.python.org/downloads/) and check **"Add python.exe to PATH"** during setup.
3. **Install the watcher:** open PowerShell in this folder and run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```
   This creates a scheduled task called "ProPresenter Stage Arrangement" that starts at login, runs hidden (no window), and has no time limit. By default it writes to `%USERPROFILE%\ProPresenter Stage Text\arrangement.txt`. To use a different file: `powershell -ExecutionPolicy Bypass -File install.ps1 "C:\path\to\file.txt"`.

   Keep this folder in place after installing. If you move it, run the installer again.
4. **Link the stage text box:** in your stage layout, add a text box and link its text to that file.

To remove it: `powershell -ExecutionPolicy Bypass -File uninstall.ps1`

To run it by hand without installing: `python arrangement_watch.py [output_file]`

## If it can't find ProPresenter

The script finds the API port by looking for ProPresenter's process: `lsof` on macOS, `tasklist` and `netstat` on Windows. If that fails, set the port yourself. You'll find it in ProPresenter's Settings → Network.

- macOS: `PROPRESENTER_PORT=50001 python3 arrangement_watch.py`
- Windows: `$env:PROPRESENTER_PORT = "50001"; python arrangement_watch.py`

## Log

The script logs every change and every connection issue to `arrangement-watch.log`, next to the output file:

```
2026-09-30 12:31:01 PM ProPresenter API on port 54364
2026-09-30 12:31:01 PM live: 'Amazing Grace-1' -> wrote '1,2,4'
2026-09-30 12:34:10 PM live: 'And can it be_' -> wrote 'Default'
```

## How it works

- Checks `GET /v1/presentation/active` and `GET /v1/playlist/active` once a second.
- **API quirk:** `/v1/playlist/active` returns an empty `arrangement_name` even when an arrangement is picked. Only `arrangement_uuid` is filled in. The script looks the name up in the full playlist (`GET /v1/playlist/{id}`), which does include it, and caches it.
- Only rewrites the file when the text changes. It overwrites the same file in place, because replacing the file with a new one can break ProPresenter's link to it. If Windows refuses the write because ProPresenter has the file open, it tries again on the next check.
- Finds ProPresenter's API port on startup and again whenever the connection drops, so it keeps working if ProPresenter restarts or changes ports.

Uses only Python's standard library (Python 3.9 or newer), so there are no packages to install. macOS includes `python3`. Windows needs Python from python.org.
