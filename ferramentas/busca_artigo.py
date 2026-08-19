# -*- coding: utf-8 -*-
"""Procura um assunto no texto indexado das normas.

Serve para achar o artigo pertinente lendo a lei, em vez de deduzi-lo do que as
notas antigas citavam. Uso:

    python ferramentas/busca_artigo.py "reconhecimento de firma"
    python ferramentas/busca_artigo.py "usufruto" --norma CNPFE-GO --n 8

Pontua por quantos termos da busca aparecem no artigo e por quao perto do inicio
- artigo que trata do assunto costuma anuncia-lo no caput.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("termos", nargs="+")
    ap.add_argument("--norma", action="append", help="limita a uma norma (pode repetir)")
    ap.add_argument("--n", type=int, default=6, help="quantos artigos mostrar")
    ap.add_argument("--largura", type=int, default=190, help="caracteres de cada trecho")
    a = ap.parse_args()

    artigos = json.loads((BASE / "dados" / "artigos.json").read_text(encoding="utf-8"))
    nomes = {n["id"]: n["nome"] for n in
             json.loads((BASE / "dados" / "normas.json").read_text(encoding="utf-8"))["normas"]}

    alvo = [sa(t) for t in a.termos]
    achados = []
    for norma, lista in artigos.items():
        if a.norma and norma not in a.norma:
            continue
        for art in lista:
            t = sa(art["texto"])
            presentes = [x for x in alvo if x in t]
            if not presentes:
                continue
            primeiro = min(t.index(x) for x in presentes)
            nota = len(presentes) * 1000 - min(primeiro, 999)
            achados.append((nota, norma, art, presentes, primeiro))

    achados.sort(key=lambda x: -x[0])
    if not achados:
        print("nada encontrado para:", " ".join(a.termos))
        return
    for nota, norma, art, presentes, pos in achados[:a.n]:
        print(f"\n### {norma} {art['artigo']}   ({len(presentes)}/{len(alvo)} termos)")
        print(f"    {nomes.get(norma, norma)[:78]}")
        ini = max(0, pos - 90)
        print("    " + re.sub(r"\s+", " ", art["texto"][ini:ini + a.largura]))


if __name__ == "__main__":
    main()
