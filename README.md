# cad2html

DWG/DXF を、オフラインで開ける**自己完結型HTML**(外部ライブラリ・通信不要)に変換するツールです。

## 使い方
```
pip install ezdxf
python -m cad2html drawing.dxf            # -> drawing.html
python -m cad2html a.dxf b.dwg            # 複数一括
python -m cad2html drawing.dxf -o out.html
```
- DXF: そのまま変換できます。
- DWG: 外部コンバータが必要です(`dwg2dxf` (LibreDWG) または ODA File Converter がPATHにあれば自動利用)。無い場合はDXFで保存してください。

## ビューアの機能
ドラッグでパン / ホイール・ピンチでズーム / 全体表示 / レイヤーON-OFF / 明暗切替 / 座標表示

## 対応エンティティ
LINE, ARC, CIRCLE, ELLIPSE, SPLINE, (LW)POLYLINE(バルジ含む), SOLID, HATCH(外形線), TEXT/MTEXT, POINT, DIMENSION, INSERT(ブロック展開)
