#!/usr/bin/env python3
"""Triagem diária ANEEL: descobertas públicas, sem atribuir validade jurídica a snippets."""
import datetime as dt
import html
import json
import os
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

TZ=dt.timezone(dt.timedelta(hours=-3))
SOURCES={
 "consultas_aneel":"https://www.gov.br/aneel/pt-br/acesso-a-informacao/participacao-social/consultas-publicas",
 "noticias_aneel":"https://www.gov.br/aneel/pt-br/assuntos/noticias",
 "legislacao_aneel":"https://www.gov.br/aneel/pt-br/centrais-de-conteudos/legislacao",
}
DIRECT=re.compile(r"diamante|jorge lacerda|ctjl|pec[eé]m|itaqui",re.I)
SECTOR=re.compile(r"consulta p[uú]blica|tomada de subs[ií]dios|prorroga|retifica|prazo|procedimentos de rede|modalidade.{0,20}opera|termel[eé]tric|receita fixa|cvu|inflexibilidade|reserva de capacidade|lrcap|reequil[ií]brio|comercializa|recontabiliza",re.I)
DOC=re.compile(r"despacho|resolu[cç][aã]o|aviso|consulta|audi[eê]ncia|reuni[aã]o|diretoria|procedimentos de rede",re.I)
class Links(HTMLParser):
 def __init__(self): super().__init__();self.href=None;self.label=[];self.items=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a":self.href=dict(attrs).get("href");self.label=[]
 def handle_data(self,data):
  if self.href is not None:self.label.append(data)
 def handle_endtag(self,tag):
  if tag=="a" and self.href:
   self.items.append((" ".join(" ".join(self.label).split()),self.href))
   self.href=None
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; RadarCORE/1.0; monitoramento publico)","Accept":"text/html"})
 with urllib.request.urlopen(req,timeout=25) as r:
  if r.status!=200:raise ValueError("HTTP "+str(r.status))
  return r.read(2_000_000).decode("utf-8",errors="replace")
def main():
 now=dt.datetime.now(TZ)
 report={"executado_em":now.isoformat(),"status":"triagem_nao_equivale_a_validacao_oficial","fontes":{},"candidatos":[],"avisos":[]}
 seen=set()
 for name,url in SOURCES.items():
  try:
   p=Links();p.feed(fetch(url));count=0
   for title,href in p.items:
    link=urllib.parse.urljoin(url,html.unescape(href))
    if not link.startswith("https://") or not title or len(title)<12:continue
    if not (DIRECT.search(title) or SECTOR.search(title) or DOC.search(title)):continue
    if link in seen:continue
    seen.add(link)
    priority="alta_para_triagem" if DIRECT.search(title) or re.search(r"prorroga|retifica|prazo|consulta p[uú]blica",title,re.I) else "media_para_triagem"
    report["candidatos"].append({"titulo":title[:240],"url":link,"origem":name,"prioridade":priority,"situacao":"candidato_sem_conferencia_da_integra"})
    count+=1
   report["fontes"][name]={"status":"acessivel","links_candidatos":count}
  except Exception as exc:
   report["fontes"][name]={"status":"falha","erro":str(exc)}
   report["avisos"].append(name+": acesso falhou; não interpretar como ausência de atos")
 report["candidatos"]=report["candidatos"][:120]
 report["avisos"].append("Lista de links não é varredura exaustiva do DOU; avisos de prorrogação podem não constar nas páginas indexadas.")
 report["avisos"].append("Prazos e efeitos jurídicos somente após conferência do aviso oficial e documentos anexos.")
 out=Path("dados/auditoria/triagem-aneel.json");out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"fontes":report["fontes"],"candidatos":len(report["candidatos"]),"avisos":report["avisos"]},ensure_ascii=False))
 if not any(v["status"]=="acessivel" for v in report["fontes"].values()):raise SystemExit("Todas as fontes falharam: triagem inconclusiva")
if __name__=="__main__":main()
