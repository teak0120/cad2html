# cad2html

DWG/DXF を、オフラインで開ける**自己完結型HTML**(外部ライブラリ・通信不要)に変換するツールです。

## 使い方
```
pip install .          # または: pip install ezdxf (インストール不要で python -m cad2html でも可)
cad2html drawing.dxf                   # -> drawing.html (python -m cad2html でも可)
python -m cad2html a.dxf b.dwg            # 複数一括
python -m cad2html drawing.dxf -o out.html
```
- DXF: そのまま変換できます。
- DWG: 変換に必要な `dwg2dxf` (LibreDWG) が無ければ**初回に自動でインストール**します(キャッシュ `~/.cache/cad2html` に保存、2回目以降は再利用)。Windows は公式バイナリをダウンロード、Linux/macOS はソースをダウンロードしてビルドします(gcc と make が必要、数分かかります)。ODA File Converter がPATHにあればそちらを優先します。

## ビューアの機能
ドラッグでパン / ホイール・ピンチでズーム / 全体表示 / レイヤーON-OFF / 明暗切替 / 座標表示

## 対応エンティティ
LINE, ARC, CIRCLE, ELLIPSE, SPLINE, (LW)POLYLINE(バルジ含む), SOLID, HATCH(外形線), TEXT/MTEXT, POINT, DIMENSION, INSERT(ブロック展開)
