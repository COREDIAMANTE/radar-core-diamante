#!/usr/bin/env python3
"""Monitor diário de atos ANEEL, com rastreabilidade e sem falsos 'zero resultados'."""
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dados" / "atos-aneel.json"
BASE = "https://leis.org/aneel/lei/2026"
ANEEL_ATOS = "https://www.gov.br/aneel/pt-br/centrais-de-conteudos/atos-do-dia"
DOU_SEARCH = "https://www.in.gov.br/consulta/-/buscar/dou?delta=20&exactDate=dia&orgPrin=Minist%C3%A9rio+de+Minas+e+Energia&orgSub=Ag%C3%AAncia+Nacional+de+Energia+El%C3%A9trica&q=%2A&s=todos&sortType=0"
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
        try: prior=json.loads(DEST.read_text(encoding="utf-8"))
        except (ValueError,OSError): pass
    days=prior.get("dias",{})
    failures=[]; sources={}; discovered=[]

    # ANEEL aponta oficialmente para a busca do DOU. A página de encaminhamento
    # não é, por si só, evidência de que os atos do dia foram consultados.
    try:
        landing=fetch(ANEEL_ATOS)
        sources["aneel"]="pagina_de_encaminhamento_acessivel" if "in.gov.br" in landing else "pagina_sem_link_dou"
    except Exception as ex:
        sources["aneel"]="indisponivel"
        failures.append("Página ANEEL Atos do Dia: "+str(ex)[:150])

    # Fonte prioritária: DOU. Se a busca exigir JavaScript, autenticação ou
    # bloquear a automação, registrar inconclusivo em vez de inferir ausência.
    try:
        listing=fetch(DOU_SEARCH)
        parser=Links();parser.feed(listing)
        official=[]
        for href in parser.urls:
            u=urllib.parse.urljoin("https://www.in.gov.br/",href)
            if urllib.parse.urlparse(u).netloc in ("www.in.gov.br","in.gov.br") and re.search(r"/web/dou/-/|/en/web/dou/-/",u):
                official.append(u.split("?")[0])
        official=list(dict.fromkeys(official))
        if not official:
            sources["dou"]="listagem_nao_extraivel"
            failures.append("Busca oficial do DOU sem links de atos extraíveis; resultado não é uma varredura validada.")
        else:
            sources["dou"]="candidatos_extraidos"
            discovered.extend(("DOU",u) for u in official[:MAX_CANDIDATES])
    except Exception as ex:
        sources["dou"]="indisponivel"
        failures.append("Busca oficial do DOU indisponível: "+str(ex)[:150])

    # Leis.org é apenas fonte complementar, nunca substitui o DOU.
    try:
        listing=fetch(BASE)
        other=candidates_from_index(listing)
        if other:
            sources["leis_org"]="candidatos_extraidos"
            discovered.extend(("Leis.org",u) for u in other[:MAX_CANDIDATES])
        else:
            sources["leis_org"]="listagem_nao_extraivel"
            failures.append("Leis.org não expôs links de atos.")
    except Exception as ex:
        sources["leis_org"]="indisponivel"
        failures.append("Leis.org indisponível: "+str(ex)[:150])

    found=[];checked=0;seen=set()
    for origin,url in discovered[:MAX_CANDIDATES]:
        if url in seen: continue
        seen.add(url)
        try:
            page=fetch(url);checked+=1
            raw=textify(page)
            # Só aceitar data comprovada. Leis.org possui campo próprio;
            # DOU precisa expor data de publicação no conteúdo da matéria.
            pub=publication_date(page) if origin=="Leis.org" else None
            if origin=="DOU":
                date_patterns=[
                    r"Publicado em:\\s*(\\d{2}/\\d{2}/\\d{4})",
                    r"Publicado em\\s*(\\d{2}/\\d{2}/\\d{4})",
                    r"Publicado em\\s*(\\d{2}\\s+de\\s+[a-zç]+\\s+de\\s+\\d{4})"
                ]
                for pat in date_patterns[:2]:
                    m=re.search(pat,raw,re.I)
                    if m:
                        try:pub=dt.datetime.strptime(m.group(1),"%d/%m/%Y").date().isoformat()
                        except ValueError:pass
                        break
            if pub!=today:continue
            tags=[name for name,patterns in TERMS.items() if any(re.search(p,raw,re.I) for p in patterns)]
            if not tags:continue
            h=re.search(r"(?is)<h[12][^>]*>(.*?)</h[12]>",page)
            title=re.sub(r"\\s+"," ",textify(h.group(1))).strip() if h else url.rsplit("/",1)[-1]
            found.append({"titulo":title[:230],"url":url,"publicado_leis_org":pub if origin=="Leis.org" else None,"data_dou":pub if origin=="DOU" else None,"fonte_coleta":origin,"ativos":tags,"status":"triagem_automatica_pendente_validacao","resumo":"Correspondência textual detectada. Conferir ato, anexos e impacto antes de concluir."})
        except Exception as ex:
            failures.append("Falha ao verificar "+url[:90]+": "+str(ex)[:90])

    # Nunca publicar dias vazios como se houvesse uma edição de Atos do Dia.
    if found:
        days[today]={"data":today,"executado_em":now.isoformat(),"status":"triagem_com_resultados","candidatos_verificados":checked,"atos":found,"avisos":failures[:15],"nota":"Resultados preliminares; verificar DOU e documentos integrais."}
    prior["dias"]=dict(sorted(((k,v) for k,v in days.items() if v.get("atos")),reverse=True)[:120])
    prior["ultima_execucao"]=now.isoformat()
    prior["ultimo_status"]="resultados_preliminares" if found else "inconclusivo" if sources.get("dou")!="candidatos_extraidos" else "sem_correspondencias_na_amostra"
    prior["fontes_status"]=sources
    prior["avisos_ultima_execucao"]=failures[:15]
    prior["candidatos_verificados_ultima_execucao"]=checked
    prior["fonte"]="DOU (prioritária); ANEEL Atos do Dia (encaminhamento); Leis.org (complementar)"
    prior["timezone"]="America/Sao_Paulo"
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(prior,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    print(json.dumps({"data":today,"status":prior["ultimo_status"],"fontes":sources,"candidatos_verificados":checked,"atos":len(found)},ensure_ascii=False))
    return 0

if __name__=="__main__":sys.exit(main())
