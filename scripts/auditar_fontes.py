#!/usr/bin/env python3
"""Auditoria de disponibilidade das bases públicas do Radar CORE.
Não publica valores: descobre arquivos anuais, metadados e registra evidências.
"""
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASES = {
    "PLD diario CCEE": ("https://dadosabertos.ccee.org.br", "pld_media_diaria", "2026"),
    "PLD semanal oficial CCEE": ("https://dadosabertos.ccee.org.br", "pld_media_semanal", "2026"),
    "CVU ONS": ("https://dados.ons.org.br", "cvu-usitermica", "2026"),
    "EAR ONS": ("https://dados.ons.org.br", "ear-diario-por-subsistema", "2026"),
}
HEADERS = {"User-Agent": "Radar-CORE-auditoria/1.0 (dados publicos)", "Accept": "application/json"}
def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)
def run():
    report = {"executado_em_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "fontes": {}, "status": "parcial"}
    ok = 0
    for name, (host, dataset, year) in BASES.items():
        url = host + "/api/3/action/package_show?" + urllib.parse.urlencode({"id": dataset})
        item = {"consulta_api": url, "status": "pendente", "recursos": []}
        try:
            data = get_json(url)
            if not data.get("success"):
                raise ValueError("API não retornou success=true")
            package = data["result"]
            for res in package.get("resources", []):
                title = res.get("name", "")
                fmt = (res.get("format") or "").upper()
                if year in title and fmt in {"CSV", "XLSX", "PARQUET"}:
                    item["recursos"].append({
                        "nome": title, "formato": fmt, "url": res.get("url"),
                        "atualizado_em": res.get("last_modified") or res.get("created"),
                        "id": res.get("id"),
                    })
            item["status"] = "localizado" if item["recursos"] else "sem_recurso_anual"
            if item["status"] == "localizado": ok += 1
        except Exception as exc:
            item["erro"] = str(exc)
            item["status"] = "falha_consulta"
        report["fontes"][name] = item
    report["status"] = "metadados_localizados" if ok == len(BASES) else "parcial"
    out = Path("dados/auditoria-fontes-mais-recente.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("\nIMPORTANTE: metadados localizados NÃO significam valores numéricos validados.")
    return 0 if ok == len(BASES) else 1
if __name__ == "__main__":
    sys.exit(run())
