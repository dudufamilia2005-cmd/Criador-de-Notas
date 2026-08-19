# -*- coding: utf-8 -*-
"""A exigencia 'sem fundamentacao' cita lei dentro do proprio texto?"""
import json, re
from pathlib import Path

D = json.loads(Path(r"C:\Users\eduardo.nobrega\Desktop\Notas\.cache-texto\levantamento.json")
               .read_text(encoding="utf-8"))
exigs = [e for n in D["notas"] for e in n["exigencias"]]
sem = [e for e in exigs if not e["fundamentos"]]

LEI = re.compile(r"\b(art\.?\s*\d|artigo\s+\d|lei\s+n|lei\s+federal|lei\s+estadual|"
                 r"c[oó]digo de normas|provimento|decreto|resolu[cç][aã]o\s+n)", re.I)

inline = [e for e in sem if LEI.search(e["texto"])]
print(f"exigencias sem bloco de fundamentacao : {len(sem)}")
print(f"   dessas, citam norma no proprio texto: {len(inline)} ({len(inline)*100//len(sem)}%)")
print(f"   dessas, sem nenhuma mencao a norma  : {len(sem)-len(inline)}")
tot = len(exigs)
com = tot - (len(sem) - len(inline))
print(f"\nde {tot} exigencias, {com} tem alguma fundamentacao ({com*100//tot}%),"
      f" {tot-com} nao tem nenhuma ({(tot-com)*100//tot}%)")
print("\namostra de citacao embutida no texto:")
for e in inline[:5]:
    m = LEI.search(e["texto"])
    print("   -", re.sub(r"\s+", " ", e["texto"][max(0, m.start()-60):m.start()+90]))
