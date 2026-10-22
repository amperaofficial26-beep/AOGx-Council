"""One-time, guarded patcher for app.py in AOGx-Council.

Run from the repository root after copying providers/github.py and ui/github_panel.py:
    python apply_oauth_patch.py
The original app.py is saved as app.py.before_github_oauth.
"""
from pathlib import Path
import re
import sys

APP = Path("app.py")
if not APP.is_file():
    sys.exit("ERROR: app.py tidak ditemukan. Jalankan script ini dari root repo AOGx-Council.")

source = APP.read_text(encoding="utf-8")
if "from ui.github_panel import render_github_pr_panel" in source:
    sys.exit("app.py sudah memakai ui.github_panel; tidak ada perubahan yang diperlukan.")

old_import = "from providers.github import GitHubClient, GitHubError"
if source.count(old_import) != 1:
    sys.exit("ERROR: import GitHub tidak cocok dengan versi app.py yang diharapkan; file tidak diubah.")
source = source.replace(old_import, "from ui.github_panel import render_github_pr_panel", 1)

pattern = re.compile(
    r'(?ms)^def github_pr_panel\(\):\n.*?(?=^ss\.setdefault\("mode", "Seimbang"\)\s*$)'
)
replacement = '''def github_pr_panel():
    """Panel GitHub OAuth dengan daftar repository dan branch otomatis."""
    return render_github_pr_panel(
        st=st,
        ss=ss,
        config=config,
        router=router,
        clip=clip,
        extract_json=extract_json,
    )


'''
source, count = pattern.subn(replacement, source, count=1)
if count != 1:
    sys.exit("ERROR: fungsi github_pr_panel tidak cocok dengan versi yang diharapkan; file tidak diubah.")

# Check syntax before touching the user's file.
compile(source, str(APP), "exec")
backup = Path("app.py.before_github_oauth")
if backup.exists():
    sys.exit(f"ERROR: {backup} sudah ada. Pindahkan backup lama dahulu; app.py belum diubah.")
backup.write_text(APP.read_text(encoding="utf-8"), encoding="utf-8")
APP.write_text(source, encoding="utf-8")
print("OK: app.py diperbarui dan lolos pemeriksaan sintaks Python.")
print(f"Backup dibuat: {backup}")
print("Pastikan providers/github.py dan ui/github_panel.py sudah disalin ke lokasi yang benar.")
