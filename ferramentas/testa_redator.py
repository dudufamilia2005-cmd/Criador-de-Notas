# -*- coding: utf-8 -*-
"""Regressao do recorte do artigo: o que o redator apaga do texto da lei.

Cada caso aqui corresponde a um estrago que ja aconteceu, ou que quase
aconteceu, ao mexer nas duas expressoes regulares de notadev/redator.py:
a que tira o numero do artigo do corpo e a que junta ponto duplicado.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from notadev.redator import Redator, JUNTA_PONTOS, TIRA_NUMERO   # noqa: E402

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
JUNTA = lambda t: JUNTA_PONTOS.sub(".", t)
TIRA = lambda t: TIRA_NUMERO.sub("", t)


def main():
    falhas = []
    for regra, casos, nome in ((JUNTA, PONTUACAO, "pontuacao"),
                               (TIRA, NUMERO, "numero do artigo")):
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

    if falhas:
        print(f"\n{len(falhas)} FALHAS:")
        for f in falhas:
            print("  x", f)
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
