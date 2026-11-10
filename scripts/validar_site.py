#!/usr/bin/env python3
"""Validação estática, sem rede, antes da publicação do Radar CORE."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "index.html", ROOT / "atos.html", *sorted((ROOT / "edicoes").glob("*.html"))]
ERRORS = []
WARNINGS = []

class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []
        self.open_tags = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("id"):
            if d["id"] in self.ids:
                ERRORS.append(f"ID duplicado: {d['id']}")
            self.ids.add(d["id"])
        if tag in ("a", "link", "script", "img"):
            key = "href" if tag in ("a", "link") else "src"
            if d.get(key):
                self.links.append((tag, d[key]))
        if tag == "a" and d.get("target") == "_blank" and "noopener" not in d.get("rel", "").split():
            WARNINGS.append("Link externo com target=_blank sem noopener")
    def error(self, message):
        ERRORS.append(message)

for page in PAGES:
    if not page.is_file():
        ERRORS.append(f"Página ausente: {page}")
        continue
    html = page.read_text(encoding="utf-8")
    parser = Scan()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        ERRORS.append(f"{page.name}: HTML inválido: {exc}")
    if "<html" not in html.lower() or "</html>" not in html.lower():
        ERRORS.append(f"{page.name}: estrutura HTML incompleta")
    for tag, raw in parser.links:
        if raw.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
            if raw.startswith("#") and raw[1:] and unquote(raw[1:]) not in parser.ids:
                WARNINGS.append(f"{page.relative_to(ROOT)}: âncora inexistente {raw}")
            continue
        parts = urlsplit(raw)
        if parts.scheme in ("http", "https"):
            continue
        if parts.scheme or raw.startswith("//"):
            WARNINGS.append(f"{page.name}: URL não convencional: {raw}")
            continue
        dest = (page.parent / unquote(parts.path)).resolve()
        if not dest.is_relative_to(ROOT.resolve()) or not dest.is_file():
            ERRORS.append(f"{page.relative_to(ROOT)}: arquivo local ausente {raw}")
    if page.parent.name == "edicoes" and "../assets/core-theme.css" not in html:
        ERRORS.append(f"{page.name}: tema compartilhado ausente")
    if page.name == "index.html" and "assets/core-theme.css" not in html:
        ERRORS.append("index.html: tema compartilhado ausente")

for data in (ROOT / "dados").glob("*.json"):
    try:
        json.loads(data.read_text(encoding="utf-8"))
    except Exception as exc:
        ERRORS.append(f"{data.name}: JSON inválido: {exc}")

print(f"Radar CORE: {len(PAGES)} páginas, {len(ERRORS)} erros, {len(WARNINGS)} alertas")
for message in WARNINGS[:30]:
    print("AVISO:", message)
for message in ERRORS:
    print("ERRO:", message)
sys.exit(1 if ERRORS else 0)
