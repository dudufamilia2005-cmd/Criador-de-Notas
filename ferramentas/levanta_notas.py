# -*- coding: utf-8 -*-
"""Levantamento do acervo real de notas devolutivas.

Le todos os .docx da pasta de notas e separa cada paragrafo em tres papeis,
usando a formatacao como criterio (e nao o texto):

  TEXTO  Arial 10, corpo corrido  -> preambulo e fecho
  EXIG   Arial 10 em lista        -> a exigencia em si
  FUND   Arial 9 recuado          -> a fundamentacao legal citada logo abaixo

Gera levantamento.json com uma entrada por nota. Nao altera nenhum arquivo
de origem: a pasta do cartorio e lida somente para leitura.
"""
import json
import os, re, sys, unicodedata, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
def q(t): return W + t

ORIGEM = Path(os.environ.get("PASTA_NOTAS", ""))
DESTINO = Path(r"C:\Users\eduardo.nobrega\Desktop\Notas\.cache-texto\levantamento.json")


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def especie(nome):
    n = sem_acento(nome)
    if "impossibilidade" in n:                      return "impossibilidade"
    if "nota de nota" in n or "nota-de-nota" in n:  return "nota de nota"
    if "exigencia" in n:                            return "exigencia"
    if "devolu" in n:                               return "devolutiva"
    if "modelo" in n:                               return "modelo"
    return "(sem rotulo no nome)"


def cm(v, div=566.93):
    try: return round(int(v) / div, 2)
    except Exception: return None


def analisa_par(p):
    """Devolve (papel, texto, marcas) de um paragrafo."""
    ppr = p.find(q("pPr"))
    esq = espaco = None
    lista = False
    if ppr is not None:
        ind = ppr.find(q("ind"))
        if ind is not None and ind.get(q("left")):
            esq = cm(ind.get(q("left")))
        sp = ppr.find(q("spacing"))
        if sp is not None and sp.get(q("line")):
            espaco = int(sp.get(q("line"))) / 240
        lista = ppr.find(q("numPr")) is not None

    tamanhos, texto, negrito_sub = set(), [], []
    for r in p.findall(q("r")):
        rpr = r.find(q("rPr"))
        tam = neg = sub = None
        if rpr is not None:
            s = rpr.find(q("sz"))
            if s is not None:
                tam = int(s.get(q("val"))) / 2
                tamanhos.add(tam)
            neg = rpr.find(q("b")) is not None
            sub = rpr.find(q("u")) is not None
        t = "".join(x.text or "" for x in r.iter(q("t")))
        texto.append(t)
        if neg and sub and t.strip():
            negrito_sub.append(t)
    texto = "".join(texto).replace("\xa0", " ").strip()
    if not texto:
        return None, "", {}

    menor = min(tamanhos) if tamanhos else None
    if menor is not None and menor <= 9.5 and (esq or 0) >= 2.0:
        papel = "FUND"
    elif menor is not None and menor <= 9.5:
        papel = "FUND"
    elif lista:
        papel = "EXIG"
    else:
        papel = "TEXTO"
    return papel, texto, {"esq": esq, "entrelinhas": espaco,
                          "lista": lista, "negrito_sub": negrito_sub}


RE_ART = re.compile(r"\bArts?\.?\s*([0-9]+(?:[\-\u2013][A-Z]{1,2})?(?:\s*[\u00ba\u00b0])?)", re.I)
RE_PAR = re.compile(r"^\s*(§\s*\d+|Par[aá]grafo [uú]nico)", re.I)


def norma_ou_artigo(texto):
    """Cabecalho de norma (nome da lei) ou dispositivo citado?"""
    if RE_ART.match(texto.strip()) or RE_PAR.match(texto.strip()):
        return "artigo"
    if re.match(r"^\s*(\(\.\.\.\)|[IVX]+\s*[\u2013\-]|[a-z]\)|\d+\s*[\u2013\-])", texto.strip()):
        return "artigo"
    return "norma"


def le(caminho):
    with zipfile.ZipFile(caminho) as z:
        raiz = ET.fromstring(z.read("word/document.xml"))
    corpo = raiz.find(q("body"))
    pars = []
    for p in corpo.findall(q("p")):
        papel, texto, m = analisa_par(p)
        if papel:
            pars.append((papel, texto, m))

    preambulo, exigencias, fecho = [], [], []
    atual = None
    for papel, texto, m in pars:
        if papel == "EXIG":
            atual = {"texto": texto, "fundamentos": [],
                     "destaques": m.get("negrito_sub", [])}
            exigencias.append(atual)
        elif papel == "FUND":
            if atual is None:
                atual = {"texto": "(fundamento sem exigencia anterior)",
                         "fundamentos": [], "destaques": []}
                exigencias.append(atual)
            atual["fundamentos"].append(
                {"tipo": norma_ou_artigo(texto), "texto": texto})
        else:
            (fecho if exigencias else preambulo).append(texto)
    return preambulo, exigencias, fecho


def main():
    if not ORIGEM.is_dir():
        sys.exit(f"Pasta de origem nao encontrada: {ORIGEM}")
    saida, falhas = [], []
    for f in sorted(ORIGEM.rglob("*.docx")):
        if f.name.startswith("~$"):
            continue
        try:
            pre, exig, fec = le(f)
        except Exception as e:
            falhas.append({"arquivo": f.name, "erro": str(e)})
            continue
        saida.append({"arquivo": f.name,
                      "especie": especie(f.name),
                      "protocolo": (f.name.split(" - ")[0].strip()
                                    if " - " in f.name else None),
                      "preambulo": pre, "exigencias": exig, "fecho": fec})
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps({"notas": saida, "falhas": falhas},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"notas lidas: {len(saida)}   falhas: {len(falhas)}")
    print(f"exigencias:  {sum(len(n['exigencias']) for n in saida)}")
    print(f"gravado em:  {DESTINO}")
    for x in falhas:
        print("  FALHA", x["arquivo"], x["erro"])


if __name__ == "__main__":
    main()
