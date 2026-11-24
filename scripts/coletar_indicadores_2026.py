#!/usr/bin/env python3
"""Coleta somente leituras observadas de bases oficiais para a edição CORE.
Não publica HTML e nunca preenche dados ausentes por estimativa.
"""
import csv
import io
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

FONTES = {
 "cvu":"https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/cvu_usitermica_se/CVU_USINA_TERMICA_2026.csv",
 "cmo":"https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/cmo_se/CMO_SEMANAL_2026.csv",
 "ear":"https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/ear_subsistema_di/EAR_DIARIO_SUBSISTEMA_2026.csv",
 "pld":"https://pda-download.ccee.org.br/T09SGpnfRN-2ZaeWfHgrMw/content",
}
CODIGOS={"Jorge Lacerda A1":26,"Jorge Lacerda A2":27,"Jorge Lacerda B":25,"Jorge Lacerda C":24,"Pecém I":167,"Pecém II":163,"Itaqui":176}
def ler(nome, url):
 req=Request(url,headers={"User-Agent":"Mozilla/5.0 (CORE/1.0; open energy data)", "Accept":"text/csv,*/*"})
 with urlopen(req,timeout=32) as r: raw=r.read(6_000_000)
 txt=raw.decode("utf-8-sig",errors="replace")
 x=list(csv.DictReader(io.StringIO(txt),delimiter=";"))
 if not x or len(x[0])<3:raise ValueError("Cabeçalho CSV inválido")
 return x
def resumo(nome,rows):
 if nome=="ear":
  dt=max(x["ear_data"] for x in rows)
  return {"data":dt,"dados":[{"subsistema":x["id_subsistema"].strip(),"valor":x["ear_verif_subsistema_percentual"]} for x in rows if x["ear_data"]==dt]}
 if nome=="cmo":
  dt=max(x["din_instante"] for x in rows)
  return {"data":dt,"dados":[{"subsistema":x["id_subsistema"].strip(),"valor":x["val_cmomediasemanal"]} for x in rows if x["din_instante"]==dt]}
 if nome=="cvu":
  today=max((x["dat_iniciosemana"],int(x["num_revisao"])) for x in rows)
  matches=[x for x in rows if (x["dat_iniciosemana"],int(x["num_revisao"]))==today and x["cod_usinaplanejamento"] in {str(v) for v in CODIGOS.values()}]
  return {"inicio":today[0],"revisao":today[1],"fim":matches[0]["dat_fimsemana"] if matches else None,"dados":[{"ativo":name,"codigo":code,"nome":next((x["nom_usina"] for x in matches if x["cod_usinaplanejamento"]==str(code)),None),"valor":next((x["val_cvu"] for x in matches if x["cod_usinaplanejamento"]==str(code)),None)} for name,code in CODIGOS.items()]}
 if nome=="pld":
  import datetime
  valid=[x for x in rows if len(x.get("DIA",""))==10 and datetime.datetime.strptime(x["DIA"],"%d/%m/%Y").date().isoformat()<="2026-11-24"]
  dt=max(datetime.datetime.strptime(x["DIA"],"%d/%m/%Y").date() for x in valid)
  day=[x for x in valid if datetime.datetime.strptime(x["DIA"],"%d/%m/%Y").date()==dt]
  seven=[x for x in valid if datetime.timedelta(1)<=dt-datetime.datetime.strptime(x["DIA"],"%d/%m/%Y").date()<=datetime.timedelta(7)]
  avg=sum(float(x["PLD_MEDIA_DIA"]) for x in seven)/len(seven) if seven else None
  return {"data":dt.isoformat(),"dados":[{"submercado":x["SUBMERCADO"],"valor":x["PLD_MEDIA_DIA"]} for x in day],"media_7_dias_anteriores":round(avg,4) if avg is not None else None,"amostras_media":len(seven)}
out={"coleta":"GitHub Actions; arquivos CSV oficiais; valores não verificados independentemente"}
for name,url in FONTES.items():
 try:
  rows=ler(name,url)
  out[name]={"fonte":url,"linhas":len(rows),**resumo(name,rows)}
 except Exception as exc:
  out[name]={"fonte":url,"erro":str(exc)[:250]}
print(json.dumps(out,ensure_ascii=False))
f=Path("dados/auditoria/indicadores_2026_execucao.json");f.parent.mkdir(parents=True,exist_ok=True)
f.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
