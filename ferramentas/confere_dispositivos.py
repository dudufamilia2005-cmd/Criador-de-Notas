# -*- coding: utf-8 -*-
"""Confere cada dispositivo citado no acervo contra o texto oficial da norma.

Regra do projeto: nenhuma fundamentacao entra no catalogo sem casar com o PDF
de origem. O que nao casar fica marcado para conferencia humana - nunca e
corrigido por conta propria, porque redacao alterada por lei nova e diferente
de erro de transcricao, e so quem le sabe qual dos dois e.
"""
import json, re, unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

BASE = Path(r"C:\Users\eduardo.nobrega\Desktop\Notas")
CACHE = BASE / ".cache-texto"

normas = {n["id"]: n for n in json.loads(
    (BASE / "dados" / "normas.json").read_text(encoding="utf-8"))["normas"]}
acervo = json.loads((CACHE / "dispositivos.json").read_text(encoding="utf-8"))["dispositivos"]

_fonte = {}
def texto_fonte(id_):
    if id_ not in _fonte:
        p = CACHE / (normas[id_]["fonte"] + ".txt")
        _fonte[id_] = p.read_text(encoding="utf-8") if p.exists() else ""
    return _fonte[id_]


def norm(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn").lower()
    s = s.replace("\xa0", " ")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def janelas(fonte, numero):
    """Todos os trechos do PDF que comecam no artigo procurado.

    O texto extraido do PDF quebra o sufixo dos artigos aditados: 'Art. 440-AV'
    sai como 'Art. 440 -AV'. Por isso o hifen aceita espaco dos dois lados - sem
    isso a faixa 440-AQ a 440-AZ, incluida pelo Provimento CN 195/2025, ficava
    invisivel e o PDF parecia incompleto.
    """
    n = r"\s*[-–]\s*".join(re.escape(x) for x in re.split(r"[-–]", numero))
    pad = re.compile(rf"art\.?\s*{n}\s*(?:[ºo°]?\s*)?[\.\-\u2013\s]", re.I)
    for m in pad.finditer(fonte):
        yield fonte[m.start(): m.start() + 6000]


def _casa(a, b):
    if not a:
        return 0.0
    sm = SequenceMatcher(None, a, b, autojunk=False)
    return sum(bl.size for bl in sm.get_matching_blocks()) / len(a)


def cobertura(citado, janela):
    """Quanto da citacao existe na fonte.

    A citacao do cartorio elide trechos com '(...)'. Medir casamento continuo
    puniria justamente a citacao bem feita: o que vem depois da elisao esta
    algumas linhas adiante na lei, nao logo em seguida. Por isso cada segmento
    entre elisoes e procurado por conta propria, e o resultado e a media
    ponderada pelo tamanho de cada um.
    """
    b = norm(janela)
    partes = [norm(p) for p in re.split(r"\(\s*\.\s*\.\s*\.\s*\)", citado)]
    partes = [p for p in partes if len(p) >= 12]
    if not partes:
        return _casa(norm(citado), b)
    total = sum(len(p) for p in partes)
    return sum(_casa(p, b) * len(p) for p in partes) / total


resultado, contagem = [], Counter()
for d in acervo:
    id_ = d["norma"]
    if id_ not in normas:
        contagem["norma desconhecida"] += 1
        continue
    numero = d["artigo"].replace("Art.", "").strip()
    fonte = texto_fonte(id_)
    melhor = 0.0
    for j in janelas(fonte, numero):
        c = cobertura(d["texto_mais_usado"] or "", j)
        if c > melhor:
            melhor = c
        if melhor >= 0.97:
            break
    corrigida = None
    if melhor < 0.85:
        # A norma pode ter sido mal atribuida na extracao: um bloco que troca de
        # norma sem repetir o cabecalho arrastava a anterior. Procura em todas.
        for outro in normas:
            if outro == id_:
                continue
            alt = 0.0
            for j in janelas(texto_fonte(outro), numero):
                c = cobertura(d["texto_mais_usado"] or "", j)
                alt = max(alt, c)
                if alt >= 0.97:
                    break
            if alt > melhor and alt >= 0.85:
                melhor, corrigida = alt, outro
        if corrigida:
            id_ = corrigida

    if melhor >= 0.85:
        st = "confere" if not corrigida else "confere (norma corrigida)"
    elif melhor >= 0.55:
        st = "diverge"
    elif melhor > 0:
        st = "nao localizado"
    else:
        st = "artigo ausente na fonte"
    contagem[st] += 1
    resultado.append({"norma": id_, "norma_nome": normas[id_]["nome"], "artigo": d["artigo"],
                      "norma_original": d["norma"] if corrigida else None,
                      "vezes": d["vezes"], "cobertura": round(melhor, 3), "situacao": st,
                      "texto": d["texto_mais_usado"], "complementos": d.get("complementos", [])})

resultado.sort(key=lambda r: (-r["vezes"],))
(BASE / "dados" / "dispositivos.json").write_text(json.dumps(
    {"_leia_me": "Dispositivos citados pelo acervo, conferidos contra o PDF da norma. "
                 "situacao=confere: a redacao casa com a fonte. diverge: redacao parecida, "
                 "conferir se houve alteracao legislativa. nao localizado / artigo ausente: "
                 "nao usar sem revisao humana.",
     "dispositivos": resultado}, ensure_ascii=False, indent=1), encoding="utf-8")

tot = len(resultado)
print(f"dispositivos conferidos: {tot}\n")
for k in ("confere", "confere (norma corrigida)", "diverge", "nao localizado",
          "artigo ausente na fonte", "norma desconhecida"):
    if contagem[k]:
        cit = sum(r["vezes"] for r in resultado if r["situacao"] == k)
        print(f"  {contagem[k]:>4} dispositivos  ({cit:>4} citacoes)  {k}")

print("\n--- PRECISAM DE OLHO HUMANO (mais citados primeiro) ---")
for r in resultado:
    if not r["situacao"].startswith("confere"):
        print(f"  {r['vezes']:>3}x  {r['cobertura']:.2f}  {r['norma']:<9} {r['artigo']:<12} {r['situacao']}")

print("\n--- CONFEREM, por norma ---")
for id_ in sorted({r["norma"] for r in resultado if r["situacao"].startswith("confere")}):
    arts = [r for r in resultado if r["norma"] == id_ and r["situacao"].startswith("confere")]
    print(f"  {id_:<9} {len(arts):>3} artigos: " + ", ".join(a["artigo"].replace("Art. ", "") for a in arts[:14]))
