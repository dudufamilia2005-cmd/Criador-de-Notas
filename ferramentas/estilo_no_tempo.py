# -*- coding: utf-8 -*-
"""O estilo de redacao mudou ao longo do tempo?"""
import json
import os, re, unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ORIGEM = Path(os.environ.get("PASTA_NOTAS", ""))
D = json.loads(Path(r"C:\Users\eduardo.nobrega\Desktop\Notas\.cache-texto\levantamento.json")
               .read_text(encoding="utf-8"))

def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()

datas = {}
for f in ORIGEM.rglob("*.docx"):
    datas[f.name] = datetime.fromtimestamp(f.stat().st_mtime)

por_sem = defaultdict(lambda: {"notas": 0, "exig": 0, "disc": 0, "fund": 0})
for n in D["notas"]:
    d = datas.get(n["arquivo"])
    if not d:
        continue
    sem = f"{d.year}-S{1 if d.month <= 6 else 2}"
    b = por_sem[sem]
    b["notas"] += 1
    for e in n["exigencias"]:
        b["exig"] += 1
        if "faz-se necessar" in sa(e["texto"]) or sa(e["texto"]).startswith("verifica-se"):
            b["disc"] += 1
        if e["fundamentos"]:
            b["fund"] += 1

print(f"{'periodo':<10}{'notas':>7}{'exig':>7}{'discursivo':>13}{'c/ fundam.':>13}{'palavras/exig':>15}")
tam = defaultdict(list)
for n in D["notas"]:
    d = datas.get(n["arquivo"])
    if d:
        sem = f"{d.year}-S{1 if d.month <= 6 else 2}"
        for e in n["exigencias"]:
            tam[sem].append(len(e["texto"].split()))
for sem in sorted(por_sem):
    b = por_sem[sem]
    ex = b["exig"] or 1
    m = sum(tam[sem]) / len(tam[sem]) if tam[sem] else 0
    print(f"{sem:<10}{b['notas']:>7}{b['exig']:>7}"
          f"{b['disc']*100//ex:>11}% {b['fund']*100//ex:>11}% {m:>14.0f}")

print("\n--- exigencias SEM fundamentacao: sao curtas mesmo? ---")
curtas = [e for n in D["notas"] for e in n["exigencias"] if not e["fundamentos"]]
comf = [e for n in D["notas"] for e in n["exigencias"] if e["fundamentos"]]
print(f"  sem fundamentacao: {len(curtas):>4} exigencias, media {sum(len(e['texto'].split()) for e in curtas)/len(curtas):.0f} palavras")
print(f"  com fundamentacao: {len(comf):>4} exigencias, media {sum(len(e['texto'].split()) for e in comf)/len(comf):.0f} palavras")
print("\n  amostra das SEM fundamentacao:")
for e in curtas[:6]:
    print("   -", re.sub(r"\s+", " ", e["texto"])[:120])
