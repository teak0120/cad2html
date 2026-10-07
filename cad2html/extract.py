"""DXF -> 軽量なジオメトリ辞書への変換 (ezdxf使用)。"""
import math
import ezdxf
from ezdxf import colors
from ezdxf.path import make_path

FLATTEN_DIST = 0.01  # 相対精度は後でextentsに応じて調整


def _rgb(entity, layers):
    """(hex色 or None) を返す。None は『前景色(ACI 7)』を意味する。"""
    dxf = entity.dxf
    if dxf.hasattr("true_color") and dxf.true_color:
        r, g, b = colors.int2rgb(dxf.true_color)
        return "#%02x%02x%02x" % (r, g, b)
    aci = dxf.get("color", 256)
    if aci == 256 or aci == 0:  # BYLAYER / BYBLOCK
        lay = layers.get(dxf.get("layer", "0"))
        aci = lay["aci"] if lay else 7
        if lay and lay.get("rgb"):
            return lay["rgb"]
    if aci in (7, 255):
        return None
    r, g, b = colors.DXF_DEFAULT_COLORS[aci] >> 16 & 255, colors.DXF_DEFAULT_COLORS[aci] >> 8 & 255, colors.DXF_DEFAULT_COLORS[aci] & 255
    return "#%02x%02x%02x" % (r, g, b)


def _iter_entities(layout, depth=0):
    for e in layout:
        t = e.dxftype()
        if t == "INSERT":
            if depth > 8:
                continue
            try:
                for v in e.virtual_entities():
                    if v.dxftype() == "INSERT":
                        yield from _iter_nested(v, depth + 1)
                    else:
                        yield v
            except Exception:
                continue
        else:
            yield e


def _iter_nested(ins, depth):
    if depth > 8:
        return
    try:
        for v in ins.virtual_entities():
            if v.dxftype() == "INSERT":
                yield from _iter_nested(v, depth + 1)
            else:
                yield v
    except Exception:
        return


def extract(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    layers = {}
    for l in doc.layers:
        rgb = None
        if l.dxf.hasattr("true_color") and l.dxf.true_color:
            r, g, b = colors.int2rgb(l.dxf.true_color)
            rgb = "#%02x%02x%02x" % (r, g, b)
        layers[l.dxf.name] = {"aci": abs(l.dxf.get("color", 7)), "rgb": rgb,
                              "off": l.is_off() or l.is_frozen()}

    ents = list(_iter_entities(msp))

    # 範囲を概算して平坦化精度を決める
    polys, texts, used = [], [], set()
    pts_all = []

    def add_poly(points, layer, col, closed=False):
        if len(points) < 2:
            return
        used.add(layer)
        polys.append({"l": layer, "c": col, "p": points, "z": closed})
        pts_all.extend(points)

    raw = []
    for e in ents:
        try:
            t = e.dxftype()
            lay = e.dxf.get("layer", "0")
            if lay in layers and layers[lay]["off"]:
                continue
            col = _rgb(e, layers)
            if t in ("TEXT", "MTEXT", "ATTRIB"):
                if t == "MTEXT":
                    txt = e.plain_text()
                    ins = e.dxf.insert
                    h = e.dxf.get("char_height", 1)
                    rot = e.dxf.get("rotation", 0)
                else:
                    txt = e.dxf.text
                    ins = e.dxf.insert
                    h = e.dxf.get("height", 1)
                    rot = e.dxf.get("rotation", 0)
                if txt and txt.strip():
                    used.add(lay)
                    texts.append({"l": lay, "c": col, "t": txt, "x": ins.x, "y": ins.y,
                                  "h": h, "r": rot})
                    pts_all.append((ins.x, ins.y))
                continue
            if t == "POINT":
                p = e.dxf.location
                raw.append((e, lay, col, "pt"))
                continue
            if t in ("LINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE", "LWPOLYLINE",
                     "POLYLINE", "SOLID", "TRACE", "3DFACE", "HATCH"):
                raw.append((e, lay, col, t))
            elif t in ("DIMENSION",):
                try:
                    for v in e.virtual_entities():
                        raw.append((v, v.dxf.get("layer", lay), col, v.dxftype()))
                except Exception:
                    pass
        except Exception:
            continue

    # 第一パス: 粗い範囲
    def bbox_hint():
        xs, ys = [], []
        for e, *_ in raw[:2000]:
            try:
                if e.dxftype() == "LINE":
                    s = e.dxf.start
                    xs.append(s.x); ys.append(s.y)
                elif e.dxftype() in ("CIRCLE", "ARC"):
                    c = e.dxf.center
                    xs.append(c.x); ys.append(c.y)
                elif e.dxftype() == "LWPOLYLINE":
                    p = e.get_points("xy")[0]
                    xs.append(p[0]); ys.append(p[1])
            except Exception:
                pass
        if xs:
            return max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
        return 1000.0

    dist = bbox_hint() / 5000.0

    for e, lay, col, t in raw:
        try:
            if t == "pt":
                p = e.dxf.location
                used.add(lay)
                polys.append({"l": lay, "c": col, "p": [(p.x, p.y), (p.x, p.y)], "z": False, "pt": 1})
                pts_all.append((p.x, p.y))
            elif t in ("SOLID", "TRACE", "3DFACE"):
                vs = [e.dxf.get(n) for n in ("vtx0", "vtx1", "vtx3", "vtx2") if e.dxf.hasattr(n)]
                add_poly([(v.x, v.y) for v in vs], lay, col, True)
            elif t == "HATCH":
                for bp in e.paths:
                    try:
                        p = None
                        if bp.PATH_TYPE == "PolylinePath":
                            pl = [(v[0], v[1]) for v in bp.vertices]
                            add_poly(pl, lay, col, True)
                        else:
                            from ezdxf.path import from_hatch_edge_path
                            path = from_hatch_edge_path(bp)
                            pl = [(v.x, v.y) for v in path.flattening(dist)]
                            add_poly(pl, lay, col, True)
                    except Exception:
                        pass
            else:
                path = make_path(e)
                for sub in path.sub_paths():
                    pl = [(v.x, v.y) for v in sub.flattening(dist, segments=8)]
                    add_poly(pl, lay, col, sub.is_closed)
        except Exception:
            continue

    if pts_all:
        xs = [p[0] for p in pts_all]; ys = [p[1] for p in pts_all]
        bbox = [min(xs), min(ys), max(xs), max(ys)]
    else:
        bbox = [0, 0, 1, 1]

    lay_out = [{"n": n, "c": layers[n]["rgb"] or _aci_hex(layers[n]["aci"])}
               for n in sorted(used)]
    return {"bbox": bbox, "layers": lay_out, "polys": polys, "texts": texts,
            "units": int(doc.header.get("$INSUNITS", 0))}


def _aci_hex(aci):
    if aci in (7, 255, 0):
        return None
    v = colors.DXF_DEFAULT_COLORS[aci]
    return "#%02x%02x%02x" % (v >> 16 & 255, v >> 8 & 255, v & 255)
