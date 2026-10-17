"""Converte um .md em HTML autonomo (sem dependencias externas no navegador). Uso: python md2html.py entrada.md saida.html"""
import sys, markdown
src, dst = sys.argv[1], sys.argv[2]
body = markdown.markdown(open(src, encoding="utf-8").read(), extensions=["tables", "fenced_code"])
css = """:root{--bg:#fbfaf7;--fg:#1f2328;--muted:#59636e;--line:#d8dee4;--head:#f1efe9;--accent:#2f6f4f;--code:#f3f2ee}
@media (prefers-color-scheme:dark){:root{--bg:#161a1d;--fg:#e6edf3;--muted:#9aa4ad;--line:#30363d;--head:#1f252b;--accent:#7bc49b;--code:#1f252b}}
body{background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;max-width:980px;margin:0 auto;padding:24px 16px}
h1{color:var(--accent);line-height:1.25}h2{border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:2em}
table{border-collapse:collapse;width:100%;display:block;overflow-x:auto;margin:1em 0;font-size:14px}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}th{background:var(--head)}
code,pre{background:var(--code);border-radius:4px;font-family:ui-monospace,Consolas,monospace;font-size:13px}code{padding:1px 4px}
pre{padding:12px;overflow-x:auto}hr{border:0;border-top:1px solid var(--line)}"""
html = f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Relatório Bonsai</title><style>{css}</style></head><body>{body}</body></html>"
open(dst, "w", encoding="utf-8").write(html)
print(dst)
