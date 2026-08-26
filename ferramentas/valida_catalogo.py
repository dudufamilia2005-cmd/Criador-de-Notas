# -*- coding: utf-8 -*-
"""Guarda das regras do catalogo. Roda antes de confiar em qualquer nota gerada.

Reprova o catalogo quando:
  1. uma exigencia cita dispositivo que nao existe em dados/dispositivos.json;
  2. cita dispositivo cuja conferencia contra o PDF nao passou;
  3. usa {campo} que nao foi declarado nem e fragmento;
  4. declara campo que nao aparece no texto;
  5. aponta fecho inexistente.
Avisa (sem reprovar) quando a exigencia ainda nao foi revisada por registrador
ou esta sem fundamentacao.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def carrega(nome):
    return json.loads((BASE / "dados" / nome).read_text(encoding="utf-8"))


def main():
    normas = {n["id"] for n in carrega("normas.json")["normas"]}
    disp = {(d["norma"], d["artigo"]): d
            for d in carrega("dispositivos.json")["dispositivos"]}
    pr = BASE / "dados" / "precedentes.json"
    precedentes = ({x["id"]: x for x in carrega("precedentes.json")["precedentes"]}
                   if pr.exists() else {})
    cat = carrega("exigencias.json")
    frag = cat["fragmentos"]
    campos_conhecidos = cat.get("campos", {})

    erros, avisos = [], []
    vistos = set()

    # campo de lista: o exemplo alimenta a tela de revisao, entao precisa ser
    # uma das opcoes - senao a revisao mostra texto que a tela nao produz
    for nome, info in campos_conhecidos.items():
        if info.get("opcoes") and info.get("exemplo") not in info["opcoes"]:
            erros.append(f"campo '{nome}': o exemplo '{info.get('exemplo')}' "
                         f"nao esta entre as opcoes")

    for e in cat["exigencias"]:
        eid = e["id"]
        if eid in vistos:
            erros.append(f"{eid}: id repetido")
        vistos.add(eid)

        texto = e["defeito"] + " " + e["providencia"]
        usados = set(re.findall(r"\{(\w+)\}", texto))
        declarados = set(e.get("campos", []))

        for c in usados - declarados - set(frag):
            erros.append(f"{eid}: usa {{{c}}}, que nao e campo declarado nem fragmento")
        for c in declarados - usados:
            erros.append(f"{eid}: declara o campo '{c}', que nao aparece no texto")
        for c in declarados - set(campos_conhecidos):
            erros.append(f"{eid}: o campo '{c}' nao tem rotulo em exigencias.json "
                         f"-> a tela pediria '{c}' ao escrevente")

        for c in set(e.get("exemplos", {})) - declarados:
            erros.append(f"{eid}: exemplo proprio para '{c}', que a exigencia nao declara")

        if e.get("fecho") not in frag:
            erros.append(f"{eid}: fecho '{e.get('fecho')}' nao existe em fragmentos")

        for pid in e.get("precedentes", []):
            p = precedentes.get(pid)
            if p is None:
                erros.append(f"{eid}: precedente '{pid}' nao existe em precedentes.json")
            elif not p.get("revisado"):
                avisos.append(f"{eid}: precedente '{pid}' ainda nao revisado")

        fund = e.get("fundamentos", [])
        if not fund and not e.get("precedentes"):
            pend = e.get("fundamentacao_pendente")
            avisos.append(f"{eid}: sem fundamentacao"
                          + (f" - {pend}" if pend else " e sem motivo declarado"))
        for f in fund:
            norma, artigo = f["norma"], f["artigo"]
            if norma not in normas:
                erros.append(f"{eid}: norma '{norma}' nao existe em normas.json")
                continue
            d = disp.get((norma, artigo))
            if d is None:
                erros.append(f"{eid}: {norma} {artigo} nao esta em dispositivos.json "
                             f"-> rode ferramentas/monta_dispositivos.py")
                continue
            # Caput que termina em dois-pontos e anuncio, nao regra: "O cancelamento
            # de hipoteca so pode ser feito:" nao diz nada sozinho, e a nota sai com
            # uma frase truncada. A regra esta nos incisos, que precisam ser apontados.
            citado = (d.get("caput", "") if not f.get("partes")
                      else ([x["texto"] for x in d.get("partes", [])
                             if x["rotulo"] == f["partes"][-1]] or [""])[0])
            if citado.rstrip().rstrip(".").endswith(":"):
                avisos.append(f"{eid}: {norma} {artigo} termina em dois-pontos - "
                              f"a regra esta nas partes que nao foram citadas")

            disponiveis = {p["rotulo"] for p in d.get("partes", [])}
            # Parte revogada nao e parte inexistente: dizer so "nao tem" mandaria
            # procurar erro de digitacao onde houve mudanca na lei.
            mortas = {x["rotulo"]: x["motivo"] for x in d.get("revogadas", [])}
            for r in f.get("partes", []):
                if r == "*":
                    continue
                if r in mortas:
                    erros.append(f"{eid}: {norma} {artigo} {r} esta REVOGADA "
                                 f"({mortas[r]}) - a nota nao pode cita-la")
                elif r not in disponiveis:
                    erros.append(f"{eid}: {norma} {artigo} nao tem a parte '{r}' "
                                 f"(tem: {', '.join(sorted(disponiveis)) or 'nenhuma'})")

            # Citar "*" traz o artigo inteiro, inclusive o que ja nao vale.
            if f.get("partes") == ["*"] and d.get("revogadas"):
                erros.append(f"{eid}: {norma} {artigo} e citado inteiro, mas tem "
                             f"parte revogada ({', '.join(x['rotulo'] for x in d['revogadas'])}) "
                             f"- aponte as partes vigentes")

        if not e.get("revisado"):
            avisos.append(f"{eid}: fundamentacao ainda nao revisada por registrador")

    print(f"catalogo: {len(cat['exigencias'])} exigencias, "
          f"{sum(len(e.get('fundamentos', [])) for e in cat['exigencias'])} fundamentos citados")
    if avisos:
        print(f"\n{len(avisos)} avisos:")
        for a in avisos:
            print("  .", a)
    if erros:
        print(f"\n{len(erros)} ERROS:")
        for x in erros:
            print("  x", x)
        return 1
    print("\nOK: todos os fundamentos conferem com a fonte e todos os campos batem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
