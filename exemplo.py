# -*- coding: utf-8 -*-
"""Gera uma nota de demonstracao, para conferir texto e formatacao."""
from pathlib import Path

from notadev.redator import Redator, Item
from notadev import documento

MOLDE = Path("modelo/molde-nota.docx")   # copia local do molde do cartorio

itens = [
    Item("transcricao-sem-caracterizacao"),
    Item("cep-nao-averbado", {"matricula": "12.345"}),
    Item("itcd-minuta", {"espolio": "Maria de Souza"}),
    Item("dare-parcelamento-sem-quitacao"),
    Item("pacto-antenupcial-ausente",
         {"parte": "a herdeira Ana Ferreira Lima", "regime": "Comunhão Universal de Bens"}),
]

r = Redator()
blocos = r.redige(
    especie="devolutiva",
    titulo=("Formal de Partilha expedido em 10.07.2026, extraído dos autos de Inventário "
            "sob processo n.º 5000000-00.2026.8.09.0000"),
    itens=itens,
    judicial=True,
)

print(r.em_texto(blocos))

pendentes = r.nao_revisadas(itens)
if pendentes:
    print("\n" + "!" * 70)
    print("FUNDAMENTACAO NAO REVISADA POR REGISTRADOR em:", ", ".join(pendentes))
    print("!" * 70)

saida = Path("saida/exemplo-nota.docx")
saida.parent.mkdir(exist_ok=True)
documento.grava(blocos, MOLDE, saida)
print(f"\ngravado: {saida.resolve()}")
