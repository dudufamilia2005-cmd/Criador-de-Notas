# -*- coding: utf-8 -*-
"""Regressao do recorte do artigo: o que o redator apaga do texto da lei.

Cada caso aqui corresponde a um estrago que ja aconteceu, ou que quase
aconteceu, ao mexer nas duas expressoes regulares de notadev/redator.py:
a que tira o numero do artigo do corpo e a que junta ponto duplicado.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from notadev.redator import (Redator, JUNTA_PONTOS, MILHAR,        # noqa: E402
                             PONTO_ORFAO,
                             TIRA_NUMERO)
from notadev.catalogo import Catalogo                            # noqa: E402

# (entrada, saida esperada, o que se protege)
PONTUACAO = [
    ("Lei nº 6.015/73.. (...) § 1º Fazem jus",
     "Lei nº 6.015/73. (...) § 1º Fazem jus",
     "ponto duplo do art. 211-A colapsa, mas o (...) do recorte fica"),
    ("no financiamento ... (Vetado) ... de habitações",
     "no financiamento ... (Vetado) ... de habitações",
     "a reticencia de trecho vetado nao e ponto duplicado"),
    ("não atribuídos ao Livro nº 3.....",
     "não atribuídos ao Livro nº 3.",
     "sobra de pontos no fim do artigo"),
    ("II - a averbação: (...) 4) da mudança",
     "II - a averbação: (...) 4) da mudança",
     "dois-pontos seguido de omissao continua intacto"),
    ("os casos previstos no art. 68 desta Lei:. (...) § 1º",
     "os casos previstos no art. 68 desta Lei: (...) § 1º",
     "ponto orfao da anotacao removida, depois de dois-pontos"),
    ("art. 5º, inciso I; e o art. 6º.",
     "art. 5º, inciso I; e o art. 6º.",
     "ponto legitimo no fim da frase nao e tocado"),
]

MILHAR_CASOS = [
    ("Art. 1063", "Art. 1.063", "artigo de quatro digitos ganha o ponto de milhar"),
    ("Art. 1410", "Art. 1.410", "o mesmo no Codigo Civil"),
    ("Art. 176", "Art. 176", "tres digitos nao mudam"),
    ("Art. 440-AQ", "Art. 440-AQ", "sufixo de letra nao e tocado"),
    ("Art. 211-A", "Art. 211-A", "nem o do codigo goiano"),
]

NUMERO = [
    ("Art. 440 -AV Os documentos...", "Os documentos...",
     "sufixo separado por espaco, como o PDF do CNN escreve"),
    ("Art. 176 - O Livro nº 2 será...", "O Livro nº 2 será...",
     "o 'O' e artigo da lingua, nao sufixo do numero"),
    ("Art. 290.. Os emolumentos devidos...", "Os emolumentos devidos...",
     "numero seguido de ponto duplo"),
    ("Art. 8° O sistema financeiro da habitação...",
     "O sistema financeiro da habitação...", "ordinal com grau"),
]

# As proprias expressoes do redator, nao copias: copia nao pega regressao.
# a mesma sequencia que o redator aplica ao texto do artigo
JUNTA = lambda t: PONTO_ORFAO.sub("", JUNTA_PONTOS.sub(".", t))
TIRA = lambda t: TIRA_NUMERO.sub("", t)
MIL = lambda t: MILHAR.sub(chr(92) + "1." + chr(92) + "2", t)


def main():
    falhas = []
    for regra, casos, nome in ((JUNTA, PONTUACAO, "pontuacao"),
                               (TIRA, NUMERO, "numero do artigo"),
                               (MIL, MILHAR_CASOS, "ponto de milhar")):
        print(f"\n{nome}")
        for entrada, esperado, porque in casos:
            saiu = regra(entrada)
            ok = saiu == esperado
            print(f"  [{'ok' if ok else 'FALHA'}] {porque}")
            if not ok:
                falhas.append(f"{porque}\n      esperado: {esperado}\n      saiu:     {saiu}")

    # a nota inteira ainda monta, com fundamentacao de tres normas
    print("\nnota completa")
    r = Redator()
    texto = r.em_texto(r.redige("devolutiva", "Escritura Pública",
                                [type("I", (), {"exigencia": "desconto-50-nao-declarado",
                                                "valores": {}})()]))
    for marca in ("Lei Federal n.º 4.380/1964", "Art. 211-A.", "§ 1º Fazem jus"):
        ok = marca in texto
        print(f"  [{'ok' if ok else 'FALHA'}] cita {marca}")
        if not ok:
            falhas.append(f"a nota nao trouxe {marca}")
    ok = ".. " not in texto
    print(f"  [{'ok' if ok else 'FALHA'}] sem ponto duplo no corpo")
    if not ok:
        falhas.append("ponto duplo sobrou na nota")

    # --------------------------------------------------------------- revogacao
    # Nenhum dispositivo revogado pode chegar a nota: nem citado de proposito,
    # nem de carona no recorte de um artigo vigente.
    print("\nrevogacao")
    disp = json.loads((RAIZ / "dados" / "dispositivos.json").read_text(encoding="utf-8"))
    d77 = [x for x in disp["dispositivos"]
           if x["norma"] == "CTE-GO" and x["artigo"] == "Art. 77"]
    if not d77:
        falhas.append("CTE-GO Art. 77 saiu do catalogo - refaca este teste")
    else:
        mortas = {x["rotulo"] for x in d77[0]["revogadas"]}
        vivas = {x["rotulo"] for x in d77[0]["partes"]}
        for rotulo in ("§ 1º", "§ 2º", "§ 3º",
                       "§ 4º", "§ 5º"):
            ok = rotulo in mortas and rotulo not in vivas
            print(f"  [{'ok' if ok else 'FALHA'}] art. 77 {rotulo} fora do recorte (revogado)")
            if not ok:
                falhas.append(f"art. 77 {rotulo} continua citavel")
        for rotulo in ("§ 6º", "§ 8º", "§ 10"):
            ok = rotulo in vivas
            print(f"  [{'ok' if ok else 'FALHA'}] art. 77 {rotulo} disponivel (vigente)")
            if not ok:
                falhas.append(f"art. 77 {rotulo}, que vale, sumiu do recorte")
        ok = "Notas:" not in d77[0]["caput"]
        print(f"  [{'ok' if ok else 'FALHA'}] caput sem a nota de reducao ja vencida")
        if not ok:
            falhas.append("a reducao temporaria de base voltou ao caput do art. 77")

    # a ultima trava: mesmo apontada a dedo, a parte revogada nao e impressa
    try:
        Catalogo().texto_dispositivo("CTE-GO", "Art. 77", ["§ 5º"])
        print("  [FALHA] citar parte revogada deveria dar erro")
        falhas.append("texto_dispositivo imprimiu parte revogada")
    except KeyError as erro:
        ok = "revogada" in str(erro)
        print(f"  [{'ok' if ok else 'FALHA'}] citar parte revogada e recusado, com o motivo")
        if not ok:
            falhas.append(f"recusou sem explicar: {erro}")

    if falhas:
        print(f"\n{len(falhas)} FALHAS:")
        for f in falhas:
            print("  x", f)
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
