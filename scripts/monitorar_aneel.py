#!/usr/bin/env python3
"""Triagem de publicacoes DIRETAS aos ativos CORE, com XML oficial do DOU quando acessivel.
Nao publica automaticamente: candidatos exigem conferencia editorial do documento.
"""
import datetime as dt
import html
import http.cookiejar
import io
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path

TZ = dt.timezone(dt.timedelta(hours=-3))
BASE = "https://inlabs.in.gov.br/"
SOURCES = {
    "aneel_noticias": "https://www.gov.br/aneel/pt-br/assuntos/noticias",
    "aneel_legislacao": "https://www.gov.br/aneel/pt-br/centrais-de-conteudos/legislacao",
    "mme": "https://www.gov.br/mme/pt-br/assuntos/noticias",
    "ibama": "https://www.gov.br/ibama/pt-br/assuntos/noticias",
    "megawhat": "https://megawhat.energy/",
    "canalenergia": "https://www.canalenergia.com.br/",
}
SEARCH_TERMS = [
    '"Diamante Geração de Energia"',
    '"Complexo Termelétrico Jorge Lacerda"',
    '"Itaqui Geração de Energia"',
    '"Pecém II Geração de Energia"',
    '"Porto do Pecém Geração de Energia"',
]
DIRECT = re.compile(
    r"diamante geracao de energia|jorge lacerda|\bctjl\b|"
    r"\bcer.?ctjl\b|27[.]?093[.]?977[/]?0001[-]?57|"
    r"itaqui geracao de energia|porto do itaqui geracao|"
    r"pecem ii geracao de energia|porto do pecem geracao de energia|"
    r"\bute porto do pecem (?:i|ii|1|2)\b", re.I
)

def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value)
                   if not unicodedata.combining(c)).lower()

def direct_match(value):
    return bool(DIRECT.search(normalize(value)))

def http_get(url, opener=None, limit=4_000_000, timeout=12):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; RadarCORE/2.0; triagem publica)",
        "Accept": "text/html,application/xml,application/zip,*/*"})
    with (opener.open if opener else urllib.request.urlopen)(req, timeout=timeout) as response:
        payload = response.read(limit + 1)
        if len(payload) > limit:
            raise ValueError("resposta maior que limite de seguranca")
        return payload

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None
        self.parts = []
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data):
        if self.href is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            self.items.append((" ".join(" ".join(self.parts).split()), self.href))
            self.href = None

def scan_public_pages(report, seen):
    for name, url in SOURCES.items():
        try:
            parser = Links()
            parser.feed(http_get(url).decode("utf-8", "replace"))
            count = 0
            for title, href in parser.items:
                dest = urllib.parse.urljoin(url, html.unescape(href))
                if not dest.startswith("https://") or len(title) < 12:
                    continue
                if not direct_match(title) or dest in seen:
                    continue
                seen.add(dest)
                report["candidatos"].append({
                    "titulo": title[:240], "url": dest, "origem": name,
                    "tipo": "noticia_ou_link_para_conferencia",
                    "situacao": "pendente_de_ato_e_publicacao_oficiais"})
                count += 1
            report["fontes"][name] = {"status": "acessivel", "candidatos": count}
        except Exception as exc:
            report["fontes"][name] = {"status": "falha", "erro": str(exc)[:180]}

def scan_news_rss(report, seen):
    total = 0
    for term in SEARCH_TERMS:
        query = term + ' (ANEEL OR "Diario Oficial" OR "despacho" OR "portaria") when:14d'
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
            "q": query, "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"})
        try:
            root = ET.fromstring(http_get(url, limit=2_000_000))
            for item in root.findall(".//item"):
                title = item.findtext("title") or ""
                href = item.findtext("link") or ""
                if not direct_match(title) or not href.startswith("https://") or href in seen:
                    continue
                seen.add(href)
                report["candidatos"].append({
                    "titulo": title[:240], "url": href,
                    "origem": "noticias_indexadas",
                    "tipo": "alerta_de_imprensa_nao_e_ato",
                    "situacao": "pendente_de_ato_e_publicacao_oficiais"})
                total += 1
        except Exception as exc:
            report["avisos"].append("RSS indexado indisponivel para um termo: " + str(exc)[:120])
    report["fontes"]["noticias_indexadas"] = {"status": "consultado", "candidatos": total}

def inlabs_opener():
    email = os.getenv("INLABS_EMAIL", "").strip()
    password = os.getenv("INLABS_PASSWORD", "").strip()
    if not email or not password:
        return None
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    payload = urllib.parse.urlencode({"email": email, "password": password}).encode()
    req = urllib.request.Request(BASE + "logar.php", data=payload,
                                 headers={"Content-Type": "application/x-www-form-urlencoded",
                                          "User-Agent": "Mozilla/5.0"})
    with opener.open(req, timeout=20) as response:
        response.read(3000)
    if not any(c.name == "inlabs_session_cookie" for c in jar):
        raise RuntimeError("INLABS nao confirmou sessao; verificar usuario e senha")
    return opener

def iter_articles(payload):
    """Retorna (metadados, texto) para cada XML do ZIP, sem extrair arquivos no disco."""
    if not payload.startswith(b"PK"):
        raise ValueError("INLABS nao retornou um ZIP valido")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for entry in archive.infolist():
            if not entry.filename.lower().endswith(".xml") or entry.file_size > 8_000_000:
                continue
            with archive.open(entry) as f:
                raw = f.read(8_000_001)
            if len(raw) > 8_000_000:
                continue
            try:
                root = ET.fromstring(raw)
            except ET.ParseError:
                continue
            nodes = ([root] if root.tag.split("}")[-1].lower() in ("article", "materia")
                     else [node for node in root.iter() if node.tag.split("}")[-1].lower() in ("article", "materia")])
            for node in nodes:
                body = html.unescape(" ".join(node.itertext()))
                if body.strip():
                    yield ({"arquivo": entry.filename, "atributos": dict(node.attrib)}, body)

def scan_inlabs(report, seen, now):
    opener = inlabs_opener()
    if opener is None:
        report["fontes"]["inlabs"] = {"status": "credenciais_ausentes",
                                       "observacao": "Configurar INLABS_EMAIL e INLABS_PASSWORD nos Actions Secrets"}
        return
    days = max(1, min(int(os.getenv("INLABS_LOOKBACK_DAYS", "7")), 21))
    files = 0
    errors = 0
    hits = 0
    for offset in range(days):
        date = (now.date() - dt.timedelta(days=offset)).isoformat()
        for section in ("DO1", "DO1E", "DO3", "DO3E"):
            filename = f"{date}-{section}.zip"
            url = f"{BASE}index.php?p={date}&dl={filename}"
            try:
                raw = http_get(url, opener, limit=40_000_000, timeout=25)
                if not raw.startswith(b"PK"):
                    continue
                files += 1
                for meta, text in iter_articles(raw):
                    if not direct_match(text):
                        continue
                    identity = f"{date}:{section}:{meta['arquivo']}"
                    if identity in seen:
                        continue
                    seen.add(identity)
                    attrs = meta["atributos"]
                    report["candidatos"].append({
                        "titulo": (attrs.get("name") or attrs.get("artCategory") or "Publicacao DOU")[:240],
                        "data_publicacao": date, "secao": section,
                        "arquivo_xml": meta["arquivo"], "metadados": attrs,
                        "trecho": re.sub(r"\s+", " ", text)[:900],
                        "origem": "inlabs_xml_oficial",
                        "tipo": "documento_oficial_candidato",
                        "situacao": "conferir_identidade_objeto_e_link_oficial_antes_de_publicar"})
                    hits += 1
            except urllib.error.HTTPError as exc:
                if exc.code not in (404, 400):
                    errors += 1
                    report["avisos"].append(f"INLABS {date} {section}: HTTP {exc.code}")
            except Exception as exc:
                errors += 1
                report["avisos"].append(f"INLABS {date} {section}: {str(exc)[:100]}")
    report["fontes"]["inlabs"] = {"status": "xml_lido" if files else "sem_arquivos_validos",
                                   "arquivos_xml_zip_lidos": files, "candidatos": hits, "falhas": errors}

def main():
    now = dt.datetime.now(TZ)
    report = {"executado_em": now.isoformat(), "status": "inconclusivo",
              "fontes": {}, "candidatos": [], "avisos": [], "cobertura_dou_xml": False}
    seen = set()
    try:
        scan_inlabs(report, seen, now)
    except Exception as exc:
        report["fontes"]["inlabs"] = {"status": "falha", "erro": str(exc)[:200]}
    scan_public_pages(report, seen)
    scan_news_rss(report, seen)
    inlabs = report["fontes"].get("inlabs", {})
    report["cobertura_dou_xml"] = inlabs.get("status") == "xml_lido"
    report["status"] = "triagem_xml_e_imprensa" if report["cobertura_dou_xml"] else "triagem_parcial_sem_dou_xml"
    report["candidatos"] = report["candidatos"][:250]
    report["resumo"] = {
        "candidatos_total": len(report["candidatos"]),
        "candidatos_xml_oficial": sum(c["origem"] == "inlabs_xml_oficial" for c in report["candidatos"]),
        "publicados_na_aba": 0,
    }
    # Nao editar dados/atos-aneel.json sem confirmar URL, objeto e data da publicacao.
    output = Path("dados/auditoria/triagem-aneel.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "resumo": report["resumo"],
                      "fontes": report["fontes"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
