#!/usr/bin/env python3
"""Monitor diário de atos ANEEL, com rastreabilidade e sem falsos 'zero resultados'."""
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dados" / "atos-aneel.json"
BASE = "https://leis.org/aneel/lei/2026"
HEADERS = {"User-Agent": "RadarCORE-Monitor/1.0 (monitoramento regulatorio)", "Accept": "text/html,application/xml,*/*"}
TERMS = {
    "Diamante": [r"diamante\s+gera[cç][aã]o", r"grupo\s+diamante", r"27\.093\.977/0001-57"],
    "CTJL": [r"jorge\s+lacerda", r"complexo\s+termel[eé]trico\s+jorge", r"\bctjl\b", r"\b478/25\b", r"48500\.011033/2026-18"],
    "Pecém I/II": [r"pec[eé]m", r"porto\s+do\s+pec[eé]m"],
    "Itaqui": [r"itaqui", r"porto\s+do\s+itaqui"],
}
MAX_CANDIDATES = 160
class Links(HTMLParser):
    def __init__(self): super().__init__(); self.urls=[]
    def handle_starttag(self, tag, attrs):
        if tag=="a":
            a=dict(attrs); href=a.get("href","")
            if href: self.urls.append(href)

def fetch(url):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=25) as resp:
        return resp.read().decode("utf-8","replace")

def textify(s):
    s=re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>"," ",s)
    return html.unescape(re.sub(r"<[^>]+>"," ",s))

def candidates_from_index(content):
    p=Links();p.feed(content); result=[]
    for link in p.urls:
        u=urllib.parse.urljoin(BASE,link)
        if urllib.parse.urlparse(u).netloc in ("leis.org","www.leis.org") and re.search(r"/aneel/lei/(?:despacho|resolucao|portaria|2026|aviso|autorizacao)",u,re.I) and u!=BASE:
            result.append(u.split("?")[0])
    return list(dict.fromkeys(result))

def publication_date(content):
    t=textify(content)
    m=re.search(r"Data de Publica[cç][aã]o no Leis\.org\s*:\s*(\d{2}/\d{2}/\d{4})",t,re.I)
    if m:
        try:return dt.datetime.strptime(m.group(1),"%d/%m/%Y").date().isoformat()
        except ValueError:pass
    return None

def main():
    now=dt.datetime.now(ZoneInfo("America/Sao_Paulo"))
    today=now.date().isoformat()
    prior={"dias":{}}
    if DEST.exists():
        try:prior=json.loads(DEST.read_text(encoding="utf-8"))
        except (ValueError,OSError):pass
    days=prior.get("dias",{})
    failures=[]; discovered=[]; index_ok=False
    try:
        index=fetch(BASE);discovered=candidates_from_index(index)
        index_ok=bool(discovered)
        if not index_ok:failures.append("A listagem do Leis.org não expôs links de atos; pode exigir JavaScript.")
    except Exception as ex:failures.append("Listagem Leis.org indisponível: "+str(ex)[:160])
    # A página pública pode listar apenas uma janela dos atos recentes.
    if len(discovered)>MAX_CANDIDATES:
        discovered=discovered[:MAX_CANDIDATES]
        failures.append("A listagem excedeu o limite de inspeção automática.")
    found=[];checked=0
    for url in discovered:
        try:
            page=fetch(url); checked+=1
            pub=publication_date(page)
            if pub!=today:continue
            raw=textify(page)
            tags=[name for name,patterns in TERMS.items() if any(re.search(p,raw,re.I) for p in patterns)]
            if not tags:continue
            h=re.search(r"(?is)<h[12][^>]*>(.*?)</h[12]>",page)
            title=re.sub(r"\s+"," ",textify(h.group(1))).strip() if h else url.rsplit("/",1)[-1]
            found.append({"titulo":title[:230],"url":url,"publicado_leis_org":pub,"ativos":tags,"status":"localizado_no_leis_org_conferir_dou","resumo":"Correspondência textual detectada; conferir ato integral, anexos, DOU e impacto antes de concluir."})
        except Exception as ex:failures.append("Falha ao verificar "+url[:110]+": "+str(ex)[:100])
    # Não apagar uma coleta anterior quando a fonte está indisponível.
    status="parcial" if failures or not index_ok else "coleta_executada_listagem_nao_exaustiva"
    if not found and status!="coleta_executada_listagem_nao_exaustiva": status="inconclusivo"
    days[today]={"data":today,"executado_em":now.isoformat(),"status":status,"candidatos_verificados":checked,"atos":found,"avisos":failures[:15],"nota":"Nenhum resultado não prova ausência de atos. Listagem do Leis.org pode ser parcial e dinâmica; confirmar DOU."}
    prior["dias"]=dict(sorted(days.items(),reverse=True)[:120])
    prior["ultima_execucao"]=now.isoformat()
    prior["fonte"]="Leis.org (triagem); DOU/ANEEL para confirmação"
    prior["timezone"]="America/Sao_Paulo"
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(prior,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"{today}: {checked} candidatos; {len(found)} correspondências; status={status}")
    # Falha não impede guardar relatório de indisponibilidade.
    return 0

if __name__=="__main__":sys.exit(main())
