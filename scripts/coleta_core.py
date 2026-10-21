#!/usr/bin/env python3
"""Coleta auditável. Nunca altera index.html sem validação editorial."""
import csv, io, json, os, re, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

BASES = [
 ("CCEE", "pld_media_diaria", "2026"),
 ("CCEE", "pld_media_semanal", "2026"),
 ("ONS", "cvu-usitermica", "2026"),
 ("ONS", "ear-diario-por-subsistema", "2026"),
]
HOSTS = {"CCEE":"https://dadosabertos.ccee.org.br", "ONS":"https://dados.ons.org.br"}
CODES = {"Jorge Lacerda A1":"26","Jorge Lacerda A2":"27","Jorge Lacerda B":"25","Jorge Lacerda C":"24","Pecem I":"167","Pecem II":"163","Porto do Itaqui":"176"}

def request(url):
    req=urllib.request.Request(url,headers={"User-Agent":"RadarCORE-Auditoria/1.0","Accept":"application/json,text/csv,*/*"})
    with urllib.request.urlopen(req,timeout=90) as res:
        return res.read(),res.headers.get("Content-Type","")

def main():
    os.makedirs("dados/auditoria",exist_ok=True)
    out={"executado_em":datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(),"status":"coleta_nao_validada","fontes":[],"alertas":[]}
    for org,slug,year in BASES:
        record={"orgao":org,"dataset":slug,"ano":year,"status":"pendente"}
        try:
            host=HOSTS[org]
            raw,_=request(host+"/api/3/action/package_show?id="+slug)
            meta=json.loads(raw)
            if not meta.get("success"): raise ValueError("API CKAN sem sucesso")
            resources=[x for x in meta["result"]["resources"] if year in (x.get("name","")+" "+x.get("url","")) and x.get("format","").upper()=="CSV"]
            if not resources: raise ValueError("Recurso CSV 2026 nao encontrado")
            resource=resources[0]
            content,_=request(resource["url"])
            if len(content)<20: raise ValueError("Arquivo vazio")
            sample=content[:10000].decode("utf-8-sig",errors="replace")
            dialect=csv.Sniffer().sniff(sample,delimiters=";,\t|")
            reader=csv.DictReader(io.StringIO(content.decode("utf-8-sig",errors="replace")),dialect=dialect)
            headers=reader.fieldnames or []
            rows=list(reader)
            if not rows: raise ValueError("CSV sem registros")
            record.update(status="baixado_nao_validado",url=resource["url"],ultima_modificacao=resource.get("last_modified"),colunas=headers,total_linhas=len(rows))
            if slug=="cvu-usitermica":
                matches=[]
                for row in rows:
                    combined=" ".join(str(v) for v in row.values())
                    if any(re.search(r"(?<!\d)"+code+r"(?!\d)",combined) for code in CODES.values()):
                        matches.append(row)
                record["linhas_candidatas_cvu"]=matches[-250:]
                record["alerta"]="Linhas candidatas; confirmar coluna de codigo ONS, vigencia e revisao antes de publicar"
            elif slug=="pld_media_diaria":
                dates=[row for row in rows if any(d in " ".join(str(v) for v in row.values()) for d in ("21/10/2026","2026-10-21","21-10-2026"))]
                record["pld_21_10_candidatos"]=dates[:30]
                record["alerta"]="Conferir quatro submercados e unidade antes de publicar"
            else:
                record["ultimas_linhas_amostra"]=rows[-8:]
        except Exception as e:
            record["status"]="erro"
            record["erro"]=str(e)
            out["alertas"].append(org+"/"+slug+": "+str(e))
        out["fontes"].append(record)
    out["status"]="coleta_finalizada_pendente_validacao_editorial"
    with open("dados/auditoria/coleta_2026-10-21.json","w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,indent=2)
    print(json.dumps({"status":out["status"],"fontes":[{"dataset":x["dataset"],"status":x["status"],"total_linhas":x.get("total_linhas")} for x in out["fontes"]],"alertas":out["alertas"]},ensure_ascii=False))
    if any(x["status"]=="erro" for x in out["fontes"]): raise SystemExit(1)

if __name__=="__main__": main()
