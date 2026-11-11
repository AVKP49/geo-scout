"""Build pinned Tailwind assets without npm. Downloads only public upstream artifacts."""

import hashlib
import platform
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "4.1.18"
PLATFORMS = {
    ("Darwin", "arm64"): (
        "macos-arm64",
        "7f27711dceac1a580b6ad58ddac46e59202c85a6c16f2f08f6fdcdee261008e1",
    ),
    ("Linux", "x86_64"): (
        "linux-x64",
        "737becf8d4ad1115ea98df69fa94026d402ca8feb91306a035b5b004167da8dd",
    ),
}
suffix, digest = PLATFORMS[(platform.system(), platform.machine())]
binary = Path(tempfile.gettempdir()) / f"geo-tailwind-{VERSION}-{suffix}"
if not binary.exists():
    url = f"https://github.com/tailwindlabs/tailwindcss/releases/download/v{VERSION}/tailwindcss-{suffix}"
    binary.write_bytes(urllib.request.urlopen(url, timeout=60).read())
if hashlib.sha256(binary.read_bytes()).hexdigest() != digest:
    raise RuntimeError("Tailwind artifact checksum did not match the upstream release digest.")
binary.chmod(0o755)
htmx = ROOT / "static/htmx.min.js"
if not htmx.exists():
    htmx.write_bytes(
        urllib.request.urlopen(
            "https://unpkg.com/htmx.org@2.0.8/dist/htmx.min.js", timeout=30
        ).read()
    )
if (
    hashlib.sha256(htmx.read_bytes()).hexdigest()
    != "22283ef68cb7545914f0a88a1bdedc7256a703d1d580c1d255217d0a50d31313"
):
    raise RuntimeError("HTMX checksum mismatch.")
subprocess.run(
    [str(binary), "-i", "static/input.css", "-o", "static/tailwind.css", "--minify"],
    cwd=ROOT,
    check=True,
)
