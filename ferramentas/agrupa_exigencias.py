# -*- coding: utf-8 -*-
"""Agrupa as 1309 exigencias do acervo por assunto.

Para cada assunto mostra: quantas vezes aparece, a redacao mais bem acabada ja
usada (prioriza o estilo discursivo e fundamentado) e quais dispositivos
costumam acompanha-la. E daqui que sai cada entrada do catalogo - a redacao e
a fundamentacao vem do acervo, nao de invencao.
"""
import json, re, unicodedata
from collections import Counter
from pathlib import Path

BASE = Path(r"C:\Users\eduardo.nobrega\Desktop\Notas")
D = json.loads((BASE / ".cache-texto" / "levantamento.json").read_text(encoding="utf-8"))
CONF = {(d["norma"], d["artigo"]): d for d in json.loads(
    (BASE / "dados" / "dispositivos.json").read_text(encoding="utf-8"))["dispositivos"]}

def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()

TEMAS = [
 ("firma",        "Reconhecimento de firma / assinatura digital", r"reconhecimento de firma|firma reconhecida|assinatura digital|certificad[oa] digital|icp-brasil"),
 ("assinatura",   "Falta de assinatura em documento",             r"(falta|ausencia|sem|nao (consta|foi|esta)).{0,40}assinatur|assinar o requerimento|nao assinad"),
 ("requerimento", "Requerimento",                                 r"requerimento"),
 ("confront",     "Confrontantes / limites",                      r"confront|limites do imovel|declaracao de limites"),
 ("memorial",     "Memorial descritivo / peca tecnica",           r"memorial descritivo|memorial|planta"),
 ("art_tec",      "ART / responsabilidade tecnica",               r"\bart\b(?!\.)|anotacao de responsabilidade tecnica|responsavel tecnico"),
 ("geo",          "Georreferenciamento / certificacao INCRA",     r"georref|certificacao|sigef|incra"),
 ("car",          "CAR / Cadastro Ambiental Rural",               r"\bcar\b|cadastro ambiental"),
 ("ccir",         "CCIR",                                         r"\bccir\b|certificado de cadastro de imovel rural"),
 ("itr",          "ITR",                                          r"\bitr\b|imposto sobre a propriedade territorial"),
 ("cep",          "CEP",                                          r"\bcep\b|enderecamento postal"),
 ("cci",          "CCI / designacao cadastral",                   r"\bcci\b|designacao cadastral|cadastro imobiliario"),
 ("itcd",         "ITCD",                                         r"\bitcd\b|transmissao causa mortis"),
 ("itbi",         "ITBI",                                         r"\bitbi\b"),
 ("dare",         "DARE / comprovante de recolhimento",           r"\bdare|comprovante de (recolhimento|pagamento)"),
 ("qualif",       "Qualificacao das partes",                      r"qualificacao (completa|das partes)|estado civil|profissao|nacionalidade"),
 ("pacto",        "Pacto antenupcial / regime de bens",           r"pacto antenupcial|regime de bens|comunhao (universal|parcial)"),
 ("uniao",        "Uniao estavel",                                r"uniao estavel|convivente|companheir"),
 ("continuidade", "Continuidade registral",                       r"continuidade|principio da continuidade"),
 ("transcricao",  "Transcricao / falta de matricula",             r"transcricao|inexistindo matricula|matricula individualizada"),
 ("levantamento", "Certidao de levantamento",                     r"certidao de levantamento"),
 ("copia",        "Documento em copia simples",                   r"copia simples|copia nao autenticada"),
 ("onus",         "Onus / hipoteca / indisponibilidade",          r"hipoteca|penhora|indisponibilidade|\bonus\b|gravame"),
 ("espolio",      "Espolio / inventario",                         r"espolio|inventario|herdeir|formal de partilha"),
 ("obito",        "Certidao de obito",                            r"certidao de obito|averbacao do obito"),
 ("sefaz",        "Avaliacao SEFAZ / valor divergente",           r"sefaz|secretaria da economia|valor de mercado|avaliacao"),
 ("selo",         "Selo / emolumentos",                           r"\bselo\b|emolumento|custas"),
 ("usufruto",     "Usufruto",                                     r"usufrut"),
 ("procuracao",   "Procuracao / representacao",                   r"procuracao|mandato|representa"),
 ("area",         "Area divergente",                              r"area .{0,25}(divergen|errad|diferen|nao confere)|divergencia de area"),
]

def discursiva(t):
    s = sa(t)
    return ("faz-se necessar" in s) or s.startswith("verifica-se")

exigs = [(e, n) for n in D["notas"] for e in n["exigencias"]]
saida = []
for tid, rotulo, pad in TEMAS:
    p = re.compile(pad)
    achadas = [e for e, n in exigs if p.search(sa(e["texto"]))]
    if not achadas:
        continue
    # dispositivos que acompanham o tema
    disp = Counter()
    for e in achadas:
        norma = None
        for f in e["fundamentos"]:
            t = re.sub(r"\s+", " ", f["texto"]).strip()
            if f["tipo"] == "norma":
                norma = t[:70]
                continue
            m = re.match(r"\s*Arts?\.?\s*(\d+(?:[-\u2013][A-Z]{1,3})?)", t, re.I)
            if m:
                disp[("Art. " + m.group(1).upper())] += 1
    # melhores redacoes: discursiva, com fundamento, mais longa
    ordenadas = sorted(achadas, key=lambda e: (discursiva(e["texto"]),
                                               bool(e["fundamentos"]),
                                               len(e["texto"])), reverse=True)
    saida.append({"id": tid, "rotulo": rotulo, "vezes": len(achadas),
                  "discursivas": sum(1 for e in achadas if discursiva(e["texto"])),
                  "com_fundamento": sum(1 for e in achadas if e["fundamentos"]),
                  "dispositivos": disp.most_common(8),
                  "melhores": [re.sub(r"\s+", " ", e["texto"]) for e in ordenadas[:3]]})

saida.sort(key=lambda x: -x["vezes"])
(BASE / ".cache-texto" / "temas.json").write_text(
    json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"{'tema':<14}{'vezes':>6}{'discurs.':>9}{'c/fund.':>8}   dispositivos mais citados")
for t in saida:
    d = " ".join(f"{a}({n})" for a, n in t["dispositivos"][:5])
    print(f"{t['id']:<14}{t['vezes']:>6}{t['discursivas']:>9}{t['com_fundamento']:>8}   {d}")
print(f"\ntemas.json gravado com as 3 melhores redacoes de cada tema")
