#!/usr/bin/env python3
"""Auditoria de disponibilidade das bases públicas do Radar CORE.
Não publica valores: descobre arquivos anuais, metadados e registra evidências.
"""
import datetime as dt
import json
import os
import csv
import io
import re
import collections
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
def inspect_csv(url, name):
    """Extrai cabeçalho e amostra final sem inferir valores com esquema desconhecido."""
    req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read(50_000_000)
    if len(raw) >= 50_000_000:
        raise ValueError("CSV excede limite de 50 MB; revisão manual necessária")
    decoded = raw.decode("utf-8-sig", errors="replace")
    delimiter = ";" if decoded[:10000].count(";") > decoded[:10000].count(",") else ","
    reader = csv.DictReader(io.StringIO(decoded), delimiter=delimiter)
    columns = reader.fieldnames or []
    if len(columns) < 2:
        raise ValueError("CSV sem colunas reconhecíveis")
    n = 0
    last = []
    pld_latest = {}
    pld_week = collections.defaultdict(list)
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date()
    last_sunday = today - dt.timedelta(days=today.weekday()+1)
    first_monday = last_sunday - dt.timedelta(days=6)
    for row in reader:
        n += 1
        if name == "PLD diario CCEE" and {"DIA", "SUBMERCADO", "PLD_MEDIA_DIA"}.issubset(columns):
            try:
                date = dt.datetime.strptime(row["DIA"].strip(), "%d/%m/%Y").date()
                sub = row["SUBMERCADO"].strip()
                value = float(row["PLD_MEDIA_DIA"].strip().replace(",", "."))
                if date <= today and (sub not in pld_latest or date > pld_latest[sub][0]):
                    pld_latest[sub] = (date, value)
                if first_monday <= date <= last_sunday:
                    pld_week[sub].append((date, value))
            except (ValueError, KeyError, TypeError):
                pass
        last.append(row)
        if len(last) > 3:
            last.pop(0)
    computed = {}
    if name == "PLD diario CCEE":
        if len(pld_latest) != 4:
            raise ValueError("PLD: não foram encontrados os quatro submercados")
        if len(pld_week) != 4 or not all(len({d for d, _ in rows}) == 7 for rows in pld_week.values()):
            raise ValueError("PLD: semana anterior incompleta")
        computed = {
            "diario_por_submercado": {sub: {"data": d.isoformat(), "valor": v} for sub, (d, v) in pld_latest.items()},
            "semanal_calculado_por_submercado": {sub: round(sum(v for _, v in rows)/7, 2) for sub, rows in pld_week.items()},
            "semana": [first_monday.isoformat(), last_sunday.isoformat()],
            "metodologia": "media aritmetica de sete medias diarias, nao serie semanal oficial"
        }
    return {"colunas": columns, "linhas": n, "indicadores_calculados": computed, "amostra_final": last,
            "validacao_numerica": "NAO_REALIZADA",
            "observacao": "Amostra para diagnóstico; exige mapeamento de colunas e conferência dos sete códigos antes de publicar"}

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
            if item["status"] == "localizado":
                ok += 1
                csv_resources = [r for r in item["recursos"] if r["formato"] == "CSV" and r.get("url")]
                if csv_resources:
                    try:
                        item["diagnostico_csv"] = inspect_csv(csv_resources[-1]["url"], name)
                        item["status"] = "csv_inspecionado_sem_validacao_numerica"
                    except Exception as exc:
                        item["erro_csv"] = str(exc)
                        item["status"] = "csv_nao_inspecionado"
        except Exception as exc:
            item["erro"] = str(exc)
            item["status"] = "falha_consulta"
        report["fontes"][name] = item
    report["status"] = "diagnostico_parcial_sem_validacao_numerica"
    out = Path("dados/auditoria-fontes-mais-recente.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("\nIMPORTANTE: metadados localizados NÃO significam valores numéricos validados.")
    return 0 if all(v["status"] == "csv_inspecionado_sem_validacao_numerica" for v in report["fontes"].values()) else 1
if __name__ == "__main__":
    sys.exit(run())
