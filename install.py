"""Generate and install only our Nyquist tool in Audacity 4's per-user directory."""
import argparse
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--generate-only", action="store_true")
parser.add_argument("--plugin-dir", type=Path)
args = parser.parse_args()
runtime = ROOT / "runtime"
runtime.mkdir(exist_ok=True)
source = (ROOT / "plugin" / "suno-url-import.ny.in").read_text(encoding="utf-8")
runtime_lisp = runtime.as_posix().replace('"', '\\"')
generated = ROOT / "plugin" / "suno-url-import.ny"
generated.write_text(source.replace("@RUNTIME@", runtime_lisp), encoding="utf-8")
if not args.generate_only:
    destination = args.plugin_dir or Path(os.environ["APPDATA"]) / "audacity" / "Audacity4" / "Plug-Ins"
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / generated.name
    if target.exists() and target.read_bytes() != generated.read_bytes():
        shutil.copy2(target, target.with_suffix(".ny.bak"))
    shutil.copy2(generated, target)
    print("Installed:", target)
    print("Restart Audacity or rescan in Tools > Plugin manager.")
# Launcher with a fixed Python executable, quoted paths, and no console window.
pythonw = Path(sys.executable).with_name("pythonw.exe")
launcher = ROOT / "Start Suno Helper.vbs"
command = f'"{pythonw}" "{ROOT / "start_helper.pyw"}"'
launcher_lines = ['Set shell = CreateObject("WScript.Shell")']
for name in ("ffmpeg", "ffprobe"):
    variable = "SUNO_" + name.upper()
    executable = os.environ.get(variable) or shutil.which(name)
    if executable and Path(executable).is_file():
        value = str(Path(executable).resolve()).replace('"', '""')
        launcher_lines.append(f'shell.Environment("PROCESS")("{variable}") = "{value}"')
launcher_lines.append('shell.Run "' + command.replace('"', '""') + '", 0, False')
launcher.write_text("\n".join(launcher_lines) + "\n", encoding="utf-16")
print("Helper launcher:", launcher)
