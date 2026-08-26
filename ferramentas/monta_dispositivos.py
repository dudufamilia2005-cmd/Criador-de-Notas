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
# O fecha-parenteses tambem conta: a anotacao de tramitacao ("(Redacao conferida
# pela Lei no 13.772 - vigencia: 01.01.01 a 02.08.13.)") so e removida depois da
# quebra, porque e nela que se le se o dispositivo ainda vale. Enquanto ela e
# removida antes, o paragrafo seguinte deixava de ser reconhecido.
PARTE = re.compile(
    r"(?<=[;:.”\")])\s+(?=(?:§\s*\d+|Par[aá]grafo\s+[uú]nico|[IVXLC]{1,6}\s*[-–]\s|"
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
    r"renumerad[oa]|revogad[oa]|transformad[oa])\s+(?:pel[oa]|em|d[oe])[^)]{0,140}\)"
    r"|\s*\((?:vide|vig[êe]ncia)[^)]{0,140}\)"
    r"|\s*NOTAS?:\s*Reda[çc][ãa]o (?:com|sem) vig[êe]ncia[^A-ZÀ-Ú]{0,90}", re.I)

# Cabecalho e rodape de impressao do site do Planalto, que a extracao do PDF
# joga no meio do artigo: "17/08/2026, 17:23 L6.015compilada https://... 55/60".
# Alem de sujar a citacao, ele nao termina em pontuacao e por isso impedia a
# separacao do paragrafo seguinte.
RODAPE = re.compile(
    # Entre a hora e a URL o site da Economia de Goias imprime o titulo da pagina,
    # que e de outro artigo: dentro do art. 77 aparecia "I - considera-se
    # industrializado o produto...", que e do ICMS. Por isso o miolo e livre, e
    # nao mais um \S+ - so limitado em tamanho, para nao comer lei de verdade.
    r"\s*\d{1,2}/\d{1,2}/\d{4},?\s*\d{1,2}:\d{2}[\s\S]{0,300}?https?://\S+\s*\d{1,4}/\d{1,4}"
    r"|\s*https?://\S*(?:planalto|gov\.br)\S*\s*\d{0,4}/?\d{0,4}", re.I)

# Nota do compilador sobre beneficio temporario: "Notas: 1.Por forca da Lei no
# 19.871, no periodo de 25.10.17 a 24.10.18, fica reduzida para 70% a base de
# calculo...". Sao periodos ja encerrados, e sairiam na nota como se valessem -
# um cliente pode ler ali uma reducao de base que nao existe mais. Vai ate o fim
# do trecho, por isso a abertura e exigida por inteiro: "Nota: Redacao com
# vigencia..." tem regra propria, limitada, porque as vezes vem ANTES do texto
# novo do dispositivo.
NOTA_EDITORIAL = re.compile(
    r"\s*Notas?:\s*(?:\d+\s*\.\s*)?(?:Por\s+for[çc]a|Fica\s+dispensad)[\s\S]*$", re.I)

CAPUT_MINIMO = 60          # abaixo disso, "parte" achada e ruido dentro do caput


# O compilado goiano nao poe o historico entre parenteses: escreve uma linha em
# caixa alta antes do dispositivo novo. Ela colava no paragrafo anterior e, por
# nao terminar em pontuacao, impedia a separacao do seguinte - foi assim que os
# §§ 6º a 10 do art. 77 sumiram do recorte, restando so os revogados.
ALTERACAO_CAIXA_ALTA = re.compile(
    r"\s*(?:REVOGAD|ACRESCID|CONFERID|ALTERAD|RENUMERAD|SUPRIMID|SUBSTITUID)"
    r"[A-ZÀ-Ú0-9§ºª°\s.,:/-]*?VIG[ÊE]NCIA:?\s*[\d./]+\s*")

# "REVOGADO O § 5º DO ART. 77 PELO ART. 2º DA LEI Nº 21.201" - diz qual parte
# morreu. E a prova mais forte, e vale para o artigo inteiro.
REVOGA_PARTE = re.compile(
    r"REVOGAD[OA]S?\s+(?:O|A|OS|AS)?\s*((?:§+\s*\d+[ºo°]?|INCISOS?\s+[IVXLC]+|"
    r"AL[ÍI]NEAS?\s+[A-Z]|PAR[ÁA]GRAFO\s+[ÚU]NICO)(?:\s*,?\s*(?:E|,)\s*"
    r"(?:§+\s*\d+[ºo°]?|[IVXLC]+|[A-Z]))*)", re.I)

# O proprio dispositivo, quando so restou a casca: "§ 5º Revogado;"
CASCA_REVOGADA = re.compile(
    r"^\s*(?:§+\s*\d+[ºo°]?|Par[áa]grafo\s+[úu]nico|[IVXLC]{1,6}|[a-z]\))"
    r"\s*[-–.)]*\s*\(?\s*revogad[oa]\s*[;.)]*\s*$", re.I)

# Planalto: "(Revogado pela Medida Provisoria no 2.197-43, de 2001)"
REVOGADO_ENTRE_PARENTESES = re.compile(r"\(\s*revogad[oa]\s+(?:pel|em|d)[^)]{0,140}\)", re.I)

# "NOTA: Redacao com vigencia de 03.08.13 a 12.02.22" - intervalo fechado: essa
# redacao ja foi substituida. Mesma regra de indexa_normas.py, aplicada agora
# parte por parte, e nao so ao artigo inteiro.
REDACAO_VENCIDA = re.compile(
    r"vig[êe]ncia:?\s*(?:de\s*)?[\d./]{6,10}\s*(?:a|à)\s*[\d./]{6,10}", re.I)


PAGINA_SOLTA = re.compile(
    r"(?<=[.;:)])\s+\d{1,4}\s+(?=§|Par[aá]grafo|[IVXLC]{1,6}\s*[-–]\s)")


def prepara(texto):
    """Tira o que impede o corte, e so isso.

    Rodape de impressao, historico em caixa alta e numero de pagina solto nao
    terminam em pontuacao e, colados no fim de um dispositivo, faziam o proximo
    passar despercebido. As anotacoes entre parenteses ficam: sao a prova de que
    a redacao vale ou nao vale, e so saem depois, parte por parte.
    """
    texto = RODAPE.sub(" ", texto)
    texto = ALTERACAO_CAIXA_ALTA.sub(" ", texto)
    texto = PAGINA_SOLTA.sub(" ", texto)
    return re.sub(r"\s{2,}", " ", texto)


def normaliza_rotulo(t):
    """'§  5°', '§ 5o' e '§ 5º' sao o mesmo paragrafo."""
    t = re.sub(r"\s+", " ", t.strip()).upper().replace("°", "º")
    return re.sub(r"(?<=\d)O", "º", t)


def partes_revogadas(texto):
    """Rotulos que o historico do proprio codigo declara revogados."""
    fora = set()
    for m in REVOGA_PARTE.finditer(texto):
        for p in re.findall(r"§+\s*\d+[ºo°]?|Par[áa]grafo\s+[úu]nico", m.group(1), re.I):
            fora.add(normaliza_rotulo(re.sub(r"^§+", "§ ", p)))
    return fora


def esta_revogada(bruto, limpo, rotulo, fora):
    """Recebe os dois textos: a prova esta ora nas anotacoes, ora sem elas.

    'bruto' guarda as anotacoes de tramitacao - e nelas que se le "(Revogada
    pela Lei ...)" e a vigencia encerrada. 'limpo' e o que sobra: e nele que a
    casca "o) (revogada);" termina de fato no fim da linha, porque no bruto ela
    ainda vem seguida da anotacao que a alterou.
    """
    if normaliza_rotulo(rotulo) in fora:
        return "o proprio codigo declara a revogacao"
    if CASCA_REVOGADA.match(limpo):
        return "o dispositivo so tem a palavra 'revogado'"
    if REVOGADO_ENTRE_PARENTESES.search(bruto):
        return "marcada como revogada no texto"
    if REDACAO_VENCIDA.search(bruto):
        return "redacao com vigencia encerrada"
    return None


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
    """caput + partes vigentes, e a parte a parte a lista do que foi revogado.

    A revogacao e apurada no texto BRUTO: a prova mora justamente nas anotacoes
    de tramitacao que limpa_anotacoes apaga. Apurar depois da limpeza fazia o
    § 5º do art. 77 do CTE-GO - revogado em 2021 - passar por vigente.
    """
    fora = partes_revogadas(texto)
    texto = prepara(texto)
    cortes = [m.end() for m in PARTE.finditer(texto) if m.end() >= CAPUT_MINIMO]
    if not cortes:
        # tambem aqui passa pelo tira_rabicho: artigo sem partes tinha saida
        # antecipada e ficava com o titulo da subsecao seguinte grudado no fim
        return NOTA_EDITORIAL.sub("", tira_rabicho(limpa_anotacoes(texto))).strip(), [], []
    limites = [0] + cortes + [len(texto)]
    brutos = [texto[a:b].strip() for a, b in zip(limites, limites[1:])]
    brutos = [p for p in brutos if p]
    caput = NOTA_EDITORIAL.sub("", limpa_anotacoes(brutos[0])).strip()
    resto_bruto = brutos[1:]

    # Rotulo repetido e comum: o art. 440-AQ tem tres alineas "a)", uma por
    # inciso, e o art. 29 do Codigo Florestal tem quatro "§ 3º", um por redacao
    # historica. O catalogo precisa apontar sem ambiguidade, entao a repeticao
    # ganha ordinal: "a)", "a) (2)", "a) (3)".
    # A contagem do ordinal corre so entre as partes que ficam: com as revogadas
    # no meio, o "§ 4º (3)" vigente seria citado como se fosse a terceira redacao
    # historica de um paragrafo que ja nao existe.
    vistos, partes, revogadas = {}, [], []
    for bruto in resto_bruto:
        r = rotulo_parte(bruto)
        limpo = NOTA_EDITORIAL.sub("", tira_rabicho(limpa_anotacoes(bruto))).strip()
        porque = esta_revogada(bruto, limpo, r, fora)
        if porque:
            revogadas.append({"rotulo": r, "motivo": porque, "texto": limpo})
            continue
        vistos[r] = vistos.get(r, 0) + 1
        if vistos[r] > 1:
            r = f"{r} ({vistos[r]})"
        partes.append({"rotulo": r, "texto": limpo})
    return tira_rabicho(caput), partes, revogadas


def main():
    artigos = json.loads((BASE / "dados" / "artigos.json").read_text(encoding="utf-8"))
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
        caput, partes, revogadas = quebra(oficial)
        d = {"norma": norma, "artigo": art, "texto": limpa_anotacoes(oficial),
             "caput": caput, "partes": partes, "revogadas": revogadas,
             "fonte": "lei"}
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
    fora = [(d, r) for d in saida for r in d["revogadas"]]
    print(f"partes revogadas, fora do recorte: {len(fora)}")
    for d, r in fora:
        print(f"  - {d['norma']} {d['artigo']} {r['rotulo']}: {r['motivo']}")
    if ausentes:
        print(f"\nNAO ENCONTRADOS no indice ({len(ausentes)}):")
        for a in ausentes:
            print("  x", a)
    print(f"\ngravado: {p}")


if __name__ == "__main__":
    main()
