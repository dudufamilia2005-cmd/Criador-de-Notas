# -*- coding: utf-8 -*-
"""Monta dados/dispositivos.json a partir da LEI, nao das notas.

Para cada artigo que o catalogo cita, pega o texto oficial do indice das normas
(.cache-texto/artigos.json) e o quebra em partes - caput, paragrafos, incisos,
alineas. A nota cita o artigo inteiro ou so as partes que interessam; de um
jeito ou de outro o texto impresso e o da lei.
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CACHE = BASE / ".cache-texto"

# Inicio de parte: § 1º | Parágrafo único | I - | a) | 3 -
# So conta se vier depois de ponto, ponto-e-virgula ou dois-pontos: sem isso o
# "2 -" de "Livro nº 2 - Registro Geral" abria um inciso no meio do caput do
# art. 176, que saia truncado em "Art. 176 - O Livro nº".
# O fecho de aspas conta como pontuacao: lei que altera outra escreve os
# dispositivos citados entre aspas ("... comunhao parcial." 8) "Art. 267...),
# e sem isso o item seguinte nao se separava.
PARTE = re.compile(
    r"(?<=[;:.”\"])\s+(?=(?:§\s*\d+|Par[aá]grafo\s+[uú]nico|[IVXLC]{1,6}\s*[-–]\s|"
    r"[a-z]\)\s|\d{1,2}\s*[-–.)]\s))", re.U)

# Titulo de divisao do codigo: nao pertence ao artigo, so vem coloado depois dele
# porque a extracao do PDF nao marca fim de artigo.
RABICHO = re.compile(
    r"\s*(?:Subse[çc][ãa]o|Se[çc][ãa]o|CAP[IÍ]TULO|T[IÍ]TULO|LIVRO|PARTE)\s+"
    r"[IVXLC0-9][^.]{0,80}$", re.I)

# Anotacoes de tramitacao que o compilado carrega e a nota nao imprime.
ANOTACAO = re.compile(
    # A marca de tramitacao nem sempre abre o parentese: aparece tambem como
    # "(Parágrafo único acrescido pelo Provimento nº 62, de 12.08.2021)". Por
    # isso ela e procurada em qualquer ponto, exigindo o "pelo/pela" seguinte
    # para nao engolir parentese de conteudo.
    r"\s*\([^)]{0,80}?(?:inclu[ií]d[oa]|acrescid[oa]|reda[çc][ãa]o (?:dada|conferida)|"
    r"renumerad[oa]|revogad[oa])\s+(?:pel[oa]|em|d[oe])[^)]{0,140}\)"
    r"|\s*\((?:vide|vig[êe]ncia)[^)]{0,140}\)"
    r"|\s*NOTAS?:\s*Reda[çc][ãa]o (?:com|sem) vig[êe]ncia[^A-ZÀ-Ú]{0,90}", re.I)

# Cabecalho e rodape de impressao do site do Planalto, que a extracao do PDF
# joga no meio do artigo: "17/08/2026, 17:23 L6.015compilada https://... 55/60".
# Alem de sujar a citacao, ele nao termina em pontuacao e por isso impedia a
# separacao do paragrafo seguinte.
RODAPE = re.compile(
    r"\s*\d{1,2}/\d{1,2}/\d{4},?\s*\d{1,2}:\d{2}\s+\S+\s+https?://\S+\s+\d{1,4}/\d{1,4}"
    r"|\s*https?://\S*(?:planalto|gov\.br)\S*\s*\d{0,4}/?\d{0,4}", re.I)

CAPUT_MINIMO = 60          # abaixo disso, "parte" achada e ruido dentro do caput


def rotulo_parte(t):
    m = re.match(r"§\s*\d+\s*[ºo°]?", t)
    if m:
        return re.sub(r"\s+", " ", m.group(0)).strip()
    if re.match(r"Par[aá]grafo\s+[uú]nico", t, re.I):
        return "Parágrafo único"
    m = re.match(r"([IVXLC]{1,6}|[a-z]\)|\d{1,2})", t)
    return m.group(1) if m else t[:12]


def limpa_anotacoes(t):
    t = RODAPE.sub(" ", t)
    t = ANOTACAO.sub("", t)
    # Numero de pagina do PDF, que cai solto entre o fim de um periodo e o
    # inicio do proximo dispositivo: "... SEFAZ. 363 §1º. Comprova-se ..."
    t = re.sub(r"(?<=[.;:])\s+\d{1,4}\s+(?=§|Par[aá]grafo|[IVXLC]{1,6}\s*[-–]\s)", " ", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def tira_rabicho(t):
    t = RABICHO.sub("", t).strip()
    # Numero de pagina que sobra no fim do trecho ("...autenticidade. 85"). Exige
    # ponto antes para nao comer numero que faca parte da frase.
    return re.sub(r"(?<=[.;:])\s+\d{1,4}\s*$", "", t).strip()


def quebra(texto):
    """caput + partes, com as anotacoes de tramitacao removidas."""
    texto = limpa_anotacoes(texto)
    cortes = [m.end() for m in PARTE.finditer(texto) if m.end() >= CAPUT_MINIMO]
    if not cortes:
        # tambem aqui passa pelo tira_rabicho: artigo sem partes tinha saida
        # antecipada e ficava com o titulo da subsecao seguinte grudado no fim
        return tira_rabicho(texto), []
    limites = [0] + cortes + [len(texto)]
    pedacos = [texto[a:b].strip() for a, b in zip(limites, limites[1:])]
    pedacos = [p for p in pedacos if p]
    caput, resto = pedacos[0], pedacos[1:]

    # Rotulo repetido e comum: o art. 440-AQ tem tres alineas "a)", uma por
    # inciso, e o art. 29 do Codigo Florestal tem quatro "§ 3º", um por redacao
    # historica. O catalogo precisa apontar sem ambiguidade, entao a repeticao
    # ganha ordinal: "a)", "a) (2)", "a) (3)".
    vistos, partes = {}, []
    for p in resto:
        r = rotulo_parte(p)
        vistos[r] = vistos.get(r, 0) + 1
        if vistos[r] > 1:
            r = f"{r} ({vistos[r]})"
        partes.append({"rotulo": r, "texto": tira_rabicho(p)})
    return tira_rabicho(caput), partes


def main():
    artigos = json.loads((CACHE / "artigos.json").read_text(encoding="utf-8"))
    indice = {(n, a["artigo"]): a["texto"] for n, lista in artigos.items() for a in lista}

    cat = json.loads((BASE / "dados" / "exigencias.json").read_text(encoding="utf-8"))
    citados = []
    for e in cat["exigencias"]:
        for f in e.get("fundamentos", []):
            if (f["norma"], f["artigo"]) not in citados:
                citados.append((f["norma"], f["artigo"]))

    p = BASE / "dados" / "dispositivos.json"

    saida, ausentes = [], []
    for norma, art in citados:
        oficial = indice.get((norma, art))
        if not oficial:
            ausentes.append(f"{norma} {art}")
            continue
        caput, partes = quebra(oficial)
        d = {"norma": norma, "artigo": art, "texto": limpa_anotacoes(oficial),
             "caput": caput, "partes": partes, "fonte": "lei"}
        # Nada do acervo de notas entra no arquivo: ele serviu para aprender a
        # forma da nota, nao para lastrear a fundamentacao. O texto e o da lei.
        saida.append(d)

    p.write_text(json.dumps(
        {"_leia_me": "Texto oficial dos artigos que o catalogo cita, extraido dos PDFs "
                     "das normas (ferramentas/indexa_normas.py). 'partes' permite citar "
                     "so o paragrafo ou inciso pertinente.",
         "dispositivos": saida}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"dispositivos montados da lei: {len(saida)}")
    print(f"com partes destacadas       : {sum(1 for d in saida if d['partes'])}")
    if ausentes:
        print(f"\nNAO ENCONTRADOS no indice ({len(ausentes)}):")
        for a in ausentes:
            print("  x", a)
    print(f"\ngravado: {p}")


if __name__ == "__main__":
    main()
