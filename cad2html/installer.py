"""DWG変換に必要な dwg2dxf (LibreDWG) が無ければ自動で導入する。"""
import os, platform, shutil, subprocess, sys, tarfile, tempfile, urllib.request, zipfile
from pathlib import Path

VERSION = "0.13.3"
BASE = "https://github.com/LibreDWG/libredwg/releases/download/%s/" % VERSION


def cache_dir():
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or str(Path.home())
    else:
        root = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(root) / "cad2html" / ("libredwg-" + VERSION)


def _exe_name():
    return "dwg2dxf.exe" if os.name == "nt" else "dwg2dxf"


def find_installed():
    exe = shutil.which("dwg2dxf")
    if exe:
        return exe
    for p in cache_dir().rglob(_exe_name()):
        if p.is_file():
            return str(p)
    return None


def _log(msg):
    print("[cad2html] " + msg, file=sys.stderr)


def _download(url, dst):
    _log("ダウンロード中: " + url)
    with urllib.request.urlopen(url, timeout=120) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)


def _install_windows(dest):
    with tempfile.TemporaryDirectory() as td:
        z = Path(td) / "l.zip"
        _download(BASE + "libredwg-%s-win64.zip" % VERSION, z)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(dest)


def _install_source(dest):
    if not (shutil.which("gcc") or shutil.which("cc")) or not shutil.which("make"):
        raise RuntimeError("ビルドに gcc と make が必要です (例: apt install build-essential / xcode-select --install)")
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "l.tar.xz"
        _download(BASE + "libredwg-%s.tar.xz" % VERSION, t)
        with tarfile.open(t) as tf:
            tf.extractall(td)
        src = Path(td) / ("libredwg-" + VERSION)
        _log("ビルド中 (数分かかります)...")
        run = lambda *a: subprocess.run(a, cwd=src, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run("./configure", "--prefix=" + str(dest), "--disable-shared", "--disable-bindings",
            "--disable-python", "--disable-write")
        run("make", "-j%d" % (os.cpu_count() or 2))
        run("make", "install")


def ensure_dwg2dxf():
    """dwg2dxf のパスを返す。無ければ導入を試みる。失敗時は RuntimeError。"""
    exe = find_installed()
    if exe:
        return exe
    dest = cache_dir()
    _log("DWG変換ツール(LibreDWG)が見つからないため自動インストールします")
    try:
        if os.name == "nt":
            _install_windows(dest)
        else:
            _install_source(dest)
    except Exception as e:
        shutil.rmtree(dest, ignore_errors=True)
        raise RuntimeError("LibreDWGの自動インストールに失敗しました: %s\n"
                           "手動で導入するか、CADソフトでDXFに保存してから指定してください。" % e)
    exe = find_installed()
    if not exe:
        raise RuntimeError("インストール後に dwg2dxf が見つかりません")
    if os.name != "nt":
        os.chmod(exe, 0o755)
    return exe
