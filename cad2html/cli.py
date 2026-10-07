"""cad2html: DWG/DXF を自己完結型HTMLビューアに変換する。"""
import argparse, json, os, shutil, subprocess, sys, tempfile, html
from pathlib import Path
from .extract import extract
from .installer import ensure_dwg2dxf

TEMPLATE = Path(__file__).with_name("viewer.html")


def dwg_to_dxf(src, outdir):
    """DWGをDXFに変換する。ODA File Converter があれば優先、無ければ LibreDWG (自動導入)。"""
    src = Path(src).resolve()
    for name in ("ODAFileConverter", "ODAFileConverter.AppImage"):
        exe = shutil.which(name)
        if exe:
            indir = Path(outdir) / "in"; indir.mkdir()
            shutil.copy(src, indir)
            subprocess.run([exe, str(indir), str(outdir), "ACAD2018", "DXF", "0", "1", src.name],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            out = Path(outdir) / (src.stem + ".dxf")
            if out.exists():
                return out
    try:
        exe = ensure_dwg2dxf()
    except RuntimeError as e:
        raise SystemExit(str(e))
    out = Path(outdir) / (src.stem + ".dxf")
    # dwg2dxf は警告で非0終了しても出力する場合があるため、出力有無で判定する
    subprocess.run([exe, "-y", "-o", str(out), str(src)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not out.exists() or out.stat().st_size == 0:
        raise SystemExit("DWGの変換に失敗しました (未対応バージョンの可能性): %s" % src)
    _sanitize_dxf(out)
    return out


def _sanitize_dxf(path):
    """dwg2dxf が出力する不正なハンドル(5/105 = 0)の組を取り除く。ezdxf が新規採番する。"""
    raw = Path(path).read_bytes()
    nl = b"\r\n" if b"\r\n" in raw[:4096] else b"\n"
    lines = raw.split(nl)
    out, i, n = [], 0, len(lines)
    while i < n:
        if i + 1 < n and lines[i].strip() in (b"5", b"105") and lines[i + 1].strip() in (b"0", b"00"):
            i += 2
            continue
        out.append(lines[i]); i += 1
    Path(path).write_bytes(nl.join(out))


def convert(src, dst=None):
    src = Path(src)
    dst = Path(dst) if dst else src.with_suffix(".html")
    with tempfile.TemporaryDirectory() as td:
        path = src
        if src.suffix.lower() == ".dwg":
            path = dwg_to_dxf(src, td)
        elif src.suffix.lower() != ".dxf":
            raise SystemExit("対応形式は .dwg / .dxf です: %s" % src)
        data = extract(str(path))
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("__TITLE__", html.escape(src.name)).replace("__DATA__", payload)
    dst.write_text(page, encoding="utf-8")
    return dst, data


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cad2html", description=__doc__)
    ap.add_argument("input", nargs="+", help=".dwg / .dxf ファイル")
    ap.add_argument("-o", "--output", help="出力HTML (入力が1つの場合のみ)")
    a = ap.parse_args(argv)
    if a.output and len(a.input) > 1:
        ap.error("-o は入力が1つのときのみ指定できます")
    for f in a.input:
        out, d = convert(f, a.output)
        print("%s -> %s (%d図形, %d文字, %dレイヤー)" % (f, out, len(d["polys"]), len(d["texts"]), len(d["layers"])))
    return 0
