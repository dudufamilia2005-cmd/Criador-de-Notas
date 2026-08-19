# -*- coding: utf-8 -*-
"""Le levantamento.json e descreve o padrao do acervo."""
import json, re, unicodedata
from collections import Counter
from pathlib import Path

D = json.loads(Path(r"C:\Users\eduardo.nobrega\Desktop\Notas\.cache-texto\levantamento.json")
               .read_text(encoding="utf-8"))
notas = D["notas"]
exigs = [e for n in notas for e in n["exigencias"]]


def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def bloco(titulo):
    print("\n" + "=" * 78 + f"\n{titulo}\n" + "=" * 78)


bloco("1. ESPECIES DE NOTA")
for k, v in Counter(n["especie"] for n in notas).most_common():
    print(f"  {v:>4}  {k}")

bloco("2. A FORMULA - quantas exigencias seguem o padrao")
tem_verifica = sum(1 for e in exigs if sa(e["texto"]).startswith("verifica-se"))
tem_dessa = sum(1 for e in exigs if "faz-se necessar" in sa(e["texto"]))
tem_fim = sum(1 for e in exigs if "prosseguimento" in sa(e["texto"]))
tot = len(exigs)
for rot, v in (('abre com "Verifica-se que"', tem_verifica),
               ('contem "faz-se necessari(a/o)"', tem_dessa),
               ('fecha citando "prosseguimento"', tem_fim)):
    print(f"  {v:>4}/{tot}  ({v*100//tot}%)  {rot}")

bloco("3. ABERTURAS ALTERNATIVAS (quando nao e 'Verifica-se que')")
for k, v in Counter(" ".join(e["texto"].split()[:3])
                    for e in exigs
                    if not sa(e["texto"]).startswith("verifica-se")).most_common(15):
    print(f"  {v:>4}  {k}")

bloco("4. O QUE SE EXIGE - providencia pedida apos 'faz-se necessaria'")
RE_PROV = re.compile(r"faz-se necess[aá]ri[ao]s?\s+(.{0,70})", re.I)
prov = Counter()
for e in exigs:
    m = RE_PROV.search(e["texto"])
    if m:
        t = re.sub(r"\s+", " ", m.group(1))
        t = re.split(r"[,;.]", t)[0].strip()
        prov[t[:60]] += 1
for k, v in prov.most_common(25):
    print(f"  {v:>4}  {k}")

bloco("5. ASSUNTOS RECORRENTES (termo citado em quantas exigencias)")
TERMOS = {
 "CEP": r"\bcep\b", "CCI": r"\bcci\b", "ITCD": r"\bitcd", "ITBI": r"\bitbi",
 "DARE": r"\bdare", "ITR": r"\bitr\b", "CAR": r"\bcar\b", "CCIR": r"\bccir",
 "CNM": r"\bcnm\b", "georreferenciamento": r"georref|geo-ref",
 "ART / peca tecnica": r"\bart\b(?!\.)|anota[cç][aã]o de responsabilidade",
 "memorial descritivo": r"memorial", "certidao de levantamento": r"certid[aã]o de levantamento",
 "requerimento": r"requerimento", "assinatura": r"assinatura|assinad",
 "reconhecimento de firma": r"reconhecimento de firma|firma reconhecida",
 "copia simples": r"c[oó]pia simples", "pacto antenupcial": r"pacto antenupcial",
 "estado civil": r"estado civil", "profissao": r"profiss[aã]o",
 "qualificacao das partes": r"qualifica[cç][aã]o", "continuidade registral": r"continuidade",
 "matricula encerrada": r"matr[ií]cula encerrada", "transcricao": r"transcri[cç][aã]o",
 "hipoteca / onus": r"hipoteca|[oô]nus|penhora", "usufruto": r"usufruto",
 "selo": r"\bselo\b", "uniao estavel": r"uni[aã]o est[aá]vel",
 "certidao de obito": r"certid[aã]o de [oó]bito", "espolio": r"esp[oó]lio",
 "confrontante": r"confront", "area divergente": r"[aá]rea .{0,20}(divergen|errad|diferen)",
 "avaliacao SEFAZ": r"sefaz|secretaria da economia",
}
for rot, pad in sorted(TERMOS.items(),
                       key=lambda kv: -sum(1 for e in exigs if re.search(kv[1], sa(e["texto"])))):
    v = sum(1 for e in exigs if re.search(pad, sa(e["texto"])))
    if v:
        print(f"  {v:>4}  {rot}")

bloco("6. NORMAS MAIS CITADAS NA FUNDAMENTACAO")
def limpa_norma(t):
    t = re.sub(r"\s+", " ", t).strip(" :.").strip()
    return t[:78]
normas = Counter(limpa_norma(f["texto"]) for e in exigs
                 for f in e["fundamentos"] if f["tipo"] == "norma"
                 and len(f["texto"]) < 130)
for k, v in normas.most_common(20):
    print(f"  {v:>4}  {k}")

bloco("7. DISPOSITIVOS MAIS CITADOS")
RE_A = re.compile(r"^\s*(Arts?\.?\s*[0-9]+(?:[\-\u2013][A-Z]{1,3})?)", re.I)
arts = Counter()
for e in exigs:
    for f in e["fundamentos"]:
        m = RE_A.match(f["texto"])
        if m:
            arts[re.sub(r"\s+", " ", m.group(1)).replace("Arts.", "Art.").strip(" .")] += 1
for k, v in arts.most_common(30):
    print(f"  {v:>4}  {k}")

bloco("8. FUNDAMENTACAO POR EXIGENCIA")
c = Counter(len(e["fundamentos"]) for e in exigs)
print(f"  sem nenhuma fundamentacao: {c[0]} de {tot} ({c[0]*100//tot}%)")
print(f"  com 1 a 3 paragrafos:      {sum(v for k,v in c.items() if 1<=k<=3)}")
print(f"  com 4 ou mais:             {sum(v for k,v in c.items() if k>=4)}")
print(f"  media:                     {sum(k*v for k,v in c.items())/tot:.1f}")

bloco("9. TAMANHO DAS NOTAS")
qt = Counter(len(n["exigencias"]) for n in notas)
print("  exigencias por nota:", dict(sorted(qt.items())))
print(f"  media: {tot/len(notas):.1f}")

bloco("10. FECHOS - ultima frase, agrupada")
fechos = Counter()
for n in notas:
    if n["fecho"]:
        fechos[re.sub(r"\s+", " ", n["fecho"][-1])[:95]] += 1
for k, v in fechos.most_common(12):
    print(f"  {v:>4}  {k}")

bloco("11. PREAMBULOS - primeira frase, agrupada")
pre = Counter()
for n in notas:
    if n["preambulo"]:
        pre[re.sub(r"\s+", " ", n["preambulo"][0])[:95]] += 1
for k, v in pre.most_common(12):
    print(f"  {v:>4}  {k}")
