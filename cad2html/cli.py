"""cad2html: DWG/DXF を自己完結型HTMLビューアに変換する。"""
import argparse, json, os, shutil, subprocess, sys, tempfile, html
from pathlib import Path
from .extract import extract

TEMPLATE = Path(__file__).with_name("viewer.html")


def dwg_to_dxf(src, outdir):
    """外部コンバータでDWGをDXFに変換する (ODA File Converter / LibreDWG)。"""
    src = Path(src).resolve()
    exe = shutil.which("dwg2dxf")
    if exe:
        out = Path(outdir) / (src.stem + ".dxf")
        subprocess.run([exe, "-y", "-o", str(out), str(src)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if out.exists():
            return out
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
    raise SystemExit("DWGの読み込みには LibreDWG の dwg2dxf か ODA File Converter が必要です。\n"
                     "インストールするか、CADソフトでDXFに保存してから指定してください。")


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
