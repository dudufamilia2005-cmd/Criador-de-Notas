# -*- coding: utf-8 -*-
"""Monta a biblioteca de dispositivos a partir do que o acervo realmente cita.

Percorre os blocos de fundamentacao das 270 notas, identifica a norma de cada
bloco e recompoe o texto de cada artigo citado (caput + paragrafos + incisos).
"""
import json, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(r"C:\Users\eduardo.nobrega\Desktop\Notas")
D = json.loads((BASE / ".cache-texto" / "levantamento.json").read_text(encoding="utf-8"))


def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


# apelido -> (id, nome oficial, arquivo PDF na pasta Fundamentacoes)
NORMAS = [
 (r"codigo de normas|foro extrajudicial do estado de goias|provimento 46",
  "CNPFE-GO", "Código de Normas e Procedimentos do Foro Extrajudicial do Estado de Goiás "
  "(Provimento CGJ-GO n.º 46/2020)",
  "Provimento 46-2020 - CGJ-GO - Codigo de Normas e Procedimentos do Foro Extrajudicial - Atualizado ate Prov. 194-2026"),
 (r"codigo nacional de normas|provimento n?\.? ?1?49|cnn",
  "CNN-CNJ", "Código Nacional de Normas da Corregedoria Nacional de Justiça – Foro Extrajudicial "
  "(Provimento CNJ n.º 149/2023)", "Codigo nacional de normas"),
 (r"6\.?015", "LRP", "Lei Federal n.º 6.015/1973 (Lei de Registros Públicos)", "L6.015compilada"),
 (r"4\.?449", "DEC4449", "Decreto Federal n.º 4.449/2002", None),
 (r"6\.?496", "L6496", "Lei Federal n.º 6.496/1977 (ART)", None),
 (r"12\.?651", "CFLO", "Lei Federal n.º 12.651/2012 (Código Florestal)", None),
 (r"4\.?947", "L4947", "Lei Federal n.º 4.947/1966", None),
 (r"11\.?651", "CTE-GO", "Lei Estadual n.º 11.651/1991 (Código Tributário Estadual)", "Codigo tributatio de goias"),
 (r"19\.?191", "L19191", "Lei Estadual n.º 19.191/2015", None),
 (r"10\.?406|codigo civil", "CC", "Lei Federal n.º 10.406/2002 (Código Civil)", "Código civil"),
 (r"13\.?105|codigo de processo civil|\bcpc\b", "CPC", "Lei Federal n.º 13.105/2015 (CPC)", "L13105"),
 (r"8\.?935", "L8935", "Lei Federal n.º 8.935/1994", "L8935"),
 (r"9\.?514", "L9514", "Lei Federal n.º 9.514/1997", "L9514"),
 (r"10\.?267", "L10267", "Lei Federal n.º 10.267/2001", "L10267"),
 (r"resolucao n?\.? ?35|resolucao 35", "RES35", "Resolução CNJ n.º 35/2007", "Resolucao 35"),
 (r"decreto[ -]?lei n?\.? ?167|167/67", "DL167", "Decreto-Lei n.º 167/1967", "Decreto lei 167"),
 (r"4\.?829", "L4829", "Lei Federal n.º 4.829/1965", "L4829"),
 (r"6\.?515", "L6515", "Lei Federal n.º 6.515/1977 (Lei do Divórcio)", None),
 (r"codigo tributario municipal|morrinhos", "CTM", "Código Tributário Municipal de Morrinhos/GO",
  "Código Tributário Municipal de Morrinhos, Goiás"),
 (r"codigo de obras|complementar n?\.? ?120", "LC120", "Lei Complementar Municipal n.º 120/2024 (Código de Obras)",
  "2024-05-29 - Lei Complementar nº 120 (Codigo de Obras Municipal)"),
 (r"complementar n?\.? ?114", "LC114", "Lei Complementar Municipal n.º 114/2023 (ITBI)",
  "2023-10-11 - Lei Complementar n.º 114 (ITBI - Reducao aliquota para 3%)"),
]

RE_ART = re.compile(r"^\s*Arts?\.?\s*(\d+(?:[\-\u2013][A-Z]{1,3})?)", re.I)
RE_CONT = re.compile(r"^\s*(§|Par[aá]grafo|[IVXLC]+\s*[\u2013\-]|[a-z]\)|\d+\s*[\u2013\-]|\(\.\.\.\))", re.I)


def identifica(texto):
    t = sa(texto)
    for pad, id_, nome, pdf in NORMAS:
        if re.search(pad, t):
            return id_, nome, pdf
    return None, None, None


disp = defaultdict(lambda: {"texto": None, "vezes": 0, "variantes": Counter()})
norma_uso = Counter()
sem_norma = 0

# Estado da varredura: o artigo e suas continuacoes (§, incisos, alineas, "(...)")
# formam um bloco so. Guardamos o bloco INTEIRO como ele saiu de uma nota real -
# juntar depois os complementos mais frequentes produziria uma citacao costurada
# de notas diferentes, que talvez nunca tenha existido daquele jeito.
atual_chave = atual_nome = atual_pdf = None
linhas = []


def descarrega():
    global atual_chave, linhas
    if atual_chave and linhas:
        bloco = " ".join(linhas)[:2000]
        d = disp[atual_chave]
        d["vezes"] += 1
        d["variantes"][bloco] += 1
        d["norma_nome"] = atual_nome
        d["pdf"] = atual_pdf
    atual_chave, linhas = None, []


for n in D["notas"]:
    for e in n["exigencias"]:
        atual_norma = None
        descarrega()
        for f in e["fundamentos"]:
            t = re.sub(r"\s+", " ", f["texto"]).strip()
            if not t:
                continue
            if f["tipo"] == "norma":
                id_, nome, pdf = identifica(t)
                if id_:
                    descarrega()
                    atual_norma = (id_, nome, pdf)
                    norma_uso[id_] += 1
                continue
            m = RE_ART.match(t)
            if m:
                if not atual_norma:
                    sem_norma += 1
                    atual_chave = None
                    continue
                descarrega()
                art = "Art. " + m.group(1).upper().replace("\u2013", "-")
                atual_chave = (atual_norma[0], art)
                atual_nome = atual_norma[1]
                atual_pdf = atual_norma[2]
                linhas = [t]
            elif atual_chave and RE_CONT.match(t):
                # paragrafo, inciso, alinea ou "(...)": faz parte do artigo acima
                linhas.append(t)
        descarrega()

for k, d in disp.items():
    if d["variantes"]:
        d["texto"] = d["variantes"].most_common(1)[0][0]
    d["variantes"] = len(d["variantes"])
    if "complementos" in d:
        d["complementos"] = [t for t, _ in d["complementos"].most_common(6)]

saida = {"dispositivos": [
    {"norma": k[0], "norma_nome": d.get("norma_nome"), "artigo": k[1],
     "vezes": d["vezes"], "redacoes_distintas": d["variantes"],
     "texto_mais_usado": d["texto"], "complementos": d.get("complementos", []),
     "pdf": d.get("pdf")}
    for k, d in sorted(disp.items(), key=lambda kv: -kv[1]["vezes"])]}
(BASE / ".cache-texto" / "dispositivos.json").write_text(
    json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"dispositivos distintos: {len(disp)}   citacoes atribuidas: {sum(d['vezes'] for d in disp.values())}")
print(f"artigos sem norma identificada: {sem_norma}\n")
print("NORMAS CITADAS x PDF DISPONIVEL")
print(f"{'norma':<10}{'citacoes':>9}  {'PDF na pasta?':<16} nome")
pdfs = {p.stem for p in (BASE / "Fundamentações").glob("*.pdf")}
faltando = []
for id_, v in norma_uso.most_common():
    nome, pdf = next(((n, p) for _, i, n, p in NORMAS if i == id_), (id_, None))
    tem = "sim" if (pdf and pdf in pdfs) else "NAO"
    if tem == "NAO":
        faltando.append((id_, v, nome))
    print(f"{id_:<10}{v:>9}  {tem:<16} {nome[:60]}")
if faltando:
    print("\n>>> NORMAS CITADAS QUE NAO ESTAO NA PASTA DE FUNDAMENTACOES:")
    for id_, v, nome in faltando:
        print(f"    {v:>4} citacoes   {nome}")
