# -*- coding: utf-8 -*-
"""Quebra cada norma em artigos, lendo o PDF - nao as notas.

Ate aqui o texto dos artigos vinha transcrito das notas do cartorio. Isso limita
a fundamentacao ao que ja foi citado alguma vez e arrasta erros de digitacao.
Aqui a lei e lida por conta propria: cada norma vira uma lista de artigos com o
texto oficial, e o acervo passa a ser so indicio de qual artigo costuma servir a
cada exigencia.

O corte entre artigos usa numeracao crescente: "Art. 176" so abre artigo novo se
vier depois do 175. Sem isso, toda remissao no meio do texto ("nos termos do art.
176") seria confundida com o inicio de um artigo.
"""
import json
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CACHE = BASE / ".cache-texto"

# Art. 176 | Art. 1º | Art. 440-AQ | Art. 440 -AQ | Art. 88-C | Artigo 22
#
ABERTURA = re.compile(
    r"Art(?:igo)?\.?\s*(\d{1,3}(?:\.\d{3})?)\s*(?:[ºo°]\s*)?"
    # Sufixo de artigo aditado vem colado ao hifen ("195-A", "88-C", "440-AQ").
    # O hifen com espaco depois e travessao: em "Art. 176 - O Livro nº 2", o "O"
    # e artigo da lingua, nao sufixo. Espaco ANTES do hifen e tolerado porque a
    # extracao do PDF do CNN produz "Art. 440 -AV".
    # A pontuacao depois do numero pode vir repetida - a Lei 6.015 traz
    # "Art. 290.." -, e exigir um sinal so fazia o artigo ser engolido pelo
    # anterior. Foi assim que o art. 290, do desconto na primeira aquisicao,
    # sumiu do indice.
    r"(?:\s*[-–]([A-Z]{1,3})\b)?\s*[\.\-–:]*\s",
)


# "NOTA: Redação com vigência de 01.03.92 a 31.12.00" - intervalo fechado marca
# redacao ja superada. A vigente aparece sem data final, ou como "a partir de".
REDACAO_VENCIDA = re.compile(
    r"vig[êe]ncia:?\s*(?:de\s*)?[\d./]{6,10}\s*(?:a|à)\s*[\d./]{6,10}", re.I)


def chave(numero, sufixo):
    """Ordem de leitura: 440 < 440-A < 440-AA < 441."""
    peso = 0
    if sufixo:
        for c in sufixo:
            peso = peso * 27 + (ord(c) - ord("A") + 1)
    return (numero, peso)


def rotulo(numero, sufixo):
    return f"Art. {numero}" + (f"-{sufixo}" if sufixo else "")


def limpa(t):
    t = t.replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def artigos_de(texto):
    """Todos os artigos da norma, em ordem, com o texto ate o proximo."""
    aceitos = []
    ultimo = (0, 0)
    for m in ABERTURA.finditer(texto):
        num = int(m.group(1).replace(".", ""))   # "Art. 1.000" e o artigo 1000
        suf = m.group(2)
        k = chave(num, suf)
        antes = texto[max(0, m.start() - 3):m.start()]
        abre_periodo = m.start() == 0 or bool(re.search(r"[\n.;:)]\s*$", antes))

        if abre_periodo:
            # Vale mesmo voltando na numeracao: o compilado goiano traz o codigo
            # duas vezes - a redacao original e, adiante, a versao com as
            # alteracoes. Exigir numeracao sempre crescente prendia o indice na
            # primeira passagem, e o art. 77 do CTE-GO saia com a redacao de 1992.
            # Remissao no meio do texto escreve "art. 176" em minuscula, e o
            # padrao so casa "Art." com maiuscula - por isso isto e seguro.
            pass
        elif k <= ultimo or (num > ultimo[0] + 60 and ultimo != (0, 0)):
            continue                      # remissao, sumario ou indice
        aceitos.append((m.start(), rotulo(num, suf), k))
        ultimo = max(ultimo, k)

    saida = []
    for i, (ini, rot, _) in enumerate(aceitos):
        fim = aceitos[i + 1][0] if i + 1 < len(aceitos) else min(len(texto), ini + 8000)
        corpo = limpa(texto[ini:fim])
        if len(corpo) < 25:
            continue
        saida.append({"artigo": rot, "texto": corpo})
    return saida


def main():
    normas = json.loads((BASE / "dados" / "normas.json").read_text(encoding="utf-8"))["normas"]
    indice, resumo = {}, []
    for n in normas:
        p = CACHE / (n["fonte"] + ".txt")
        if not p.exists():
            resumo.append((n["id"], 0, "SEM TEXTO EXTRAIDO"))
            continue
        arts = artigos_de(p.read_text(encoding="utf-8"))
        # Artigo repetido: os textos compilados (sobretudo o goiano) trazem cada
        # redacao ja tida pelo artigo, uma abaixo da outra. A revogada carrega
        # nota de vigencia com data final - "Redacao com vigencia de X a Y" -,
        # enquanto a vigente nao tem data de fim. Pegar a mais longa, como se
        # fazia aqui, escolhia texto revogado: o art. 77 do CTE-GO saia com a
        # redacao que valeu ate 31.12.2000.
        por_rotulo = {}
        for a in arts:
            a["revogado"] = bool(REDACAO_VENCIDA.search(a["texto"][:400]))
            atual = por_rotulo.get(a["artigo"])
            if atual is None or (atual["revogado"] and not a["revogado"]):
                por_rotulo[a["artigo"]] = a
            elif atual["revogado"] == a["revogado"]:
                por_rotulo[a["artigo"]] = a   # empate: fica a ultima, que e a mais nova
        indice[n["id"]] = por_rotulo
        ultimo = arts[-1]["artigo"] if arts else "-"
        resumo.append((n["id"], len(por_rotulo), f"vai ate {ultimo}"))

    # O indice vai para dados/, e nao para o cache: sem ele o servidor nao tem o
    # que consultar, e a implantacao no Vercel so leva o que esta no repositorio.
    (BASE / "dados").mkdir(exist_ok=True)
    (BASE / "dados" / "artigos.json").write_text(
        json.dumps({k: list(v.values()) for k, v in indice.items()},
                   ensure_ascii=False), encoding="utf-8")

    print(f"{'norma':<10}{'artigos':>8}   alcance")
    for id_, n, obs in resumo:
        print(f"{id_:<10}{n:>8}   {obs}")
    total = sum(len(v) for v in indice.values())
    print(f"\ntotal: {total} artigos indexados em {len(indice)} normas")
    print(f"gravado: {BASE / 'dados' / 'artigos.json'}")


if __name__ == "__main__":
    main()
