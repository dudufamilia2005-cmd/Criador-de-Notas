# -*- coding: utf-8 -*-
"""Extrai o texto dos PDFs das normas para .cache-texto/, passo 1 do indice.

O caminho completo e:

    Fundamentações/*.pdf  ->  .cache-texto/*.txt   (aqui)
                          ->  dados/artigos.json   (indexa_normas.py)
                          ->  dados/dispositivos.json (monta_dispositivos.py)

Este passo faltava no repositorio: a extracao vinha sendo feita a mao, num
script solto, a cada norma nova. Como .cache-texto/ e descartavel e esta no
.gitignore, apaga-lo deixava o indice sem como ser refeito - indexa_normas.py
apenas anotava "SEM TEXTO EXTRAIDO" para cada norma e seguia adiante.

Os PDFs sao a fonte da verdade e estao versionados; o .txt e derivado.
"""
import argparse
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PDFS = BASE / "Fundamentações"
CACHE = BASE / ".cache-texto"


def carrega_normas():
    import json
    d = json.loads((BASE / "dados" / "normas.json").read_text(encoding="utf-8"))
    return d["normas"]


def extrai(pdf):
    from pypdf import PdfReader
    r = PdfReader(str(pdf))
    return "\n".join((p.extract_text() or "") for p in r.pages), len(r.pages)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refazer", action="store_true",
                    help="reextrai mesmo o que ja esta em dia com o PDF")
    ap.add_argument("--norma", help="so esta (id de dados/normas.json)")
    args = ap.parse_args()

    try:
        import pypdf                                            # noqa: F401
    except ImportError:
        raise SystemExit("pypdf nao esta instalado: "
                         r".venv\Scripts\python.exe -m pip install -r requirements.txt")

    CACHE.mkdir(exist_ok=True)
    feitos = pulados = 0
    faltando = []

    for n in carrega_normas():
        if args.norma and n["id"] != args.norma:
            continue
        pdf = PDFS / (n["fonte"] + ".pdf")
        txt = CACHE / (n["fonte"] + ".txt")
        if not pdf.is_file():
            faltando.append(f"{n['id']}: {pdf.name}")
            continue
        # O .txt em dia com o PDF nao e refeito: a extracao das 32 normas leva
        # minutos, e quase sempre so uma mudou.
        if txt.is_file() and txt.stat().st_mtime >= pdf.stat().st_mtime and not args.refazer:
            pulados += 1
            continue
        texto, paginas = extrai(pdf)
        txt.write_text(texto, encoding="utf-8")
        feitos += 1
        print(f"  {n['id']:<12} {paginas:>4} pag  {len(texto):>8} caracteres")

    print(f"\nextraidos: {feitos} | ja em dia: {pulados}")
    if faltando:
        print(f"\nPDF AUSENTE ({len(faltando)}) - a norma fica sem texto e sai do indice:")
        for f in faltando:
            print("  x", f)
        return 1
    if feitos:
        print("\nagora rode: ferramentas/indexa_normas.py e ferramentas/monta_dispositivos.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
