# -*- coding: utf-8 -*-
"""Serve a tela da nota devolutiva no navegador, a partir da propria maquina.

Por que navegador e nao janela nativa: o Tkinter desenha com o tema antigo do
Windows e nao tem como parecer atual; e as alternativas (Qt, wx) exigem pacotes
que nao instalam nesta Python 3.15. Com http.server da biblioteca padrao a
aparencia vira HTML e CSS, sem nenhuma dependencia nova.

Escuta so em 127.0.0.1, em porta sorteada pelo sistema: nada fica exposto na
rede do cartorio.
"""
import base64
import json
import os
import re
import unicodedata
import subprocess
import tempfile
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .catalogo import BASE
from .redator import Item, Redator
from . import documento

WEB = BASE / "public"

# No Vercel o disco e somente leitura e nao ha para onde salvar: as rotas que
# gravam ficam desligadas e a nota volta como download, em vez de virar arquivo.
SOMENTE_LEITURA = bool(os.environ.get("VERCEL"))
MOLDE = BASE / "modelo" / "molde-nota.docx"
SAIDA = BASE / "saida"

def sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn").lower()


TIPOS = {".html": "text/html; charset=utf-8",
         ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8"}


def catalogo_para_tela(r):
    cru = json.loads((BASE / "dados" / "exigencias.json").read_text(encoding="utf-8"))
    exigencias = sorted(r.cat.exigencias.values(),
                        key=lambda e: (e["assunto"], e["rotulo"]))
    return {
        "somente_leitura": SOMENTE_LEITURA,
        "especies": [{"id": k, "rotulo": v["rotulo"]}
                     for k, v in r.modelo["especies"].items()],
        "campos": cru.get("campos", {}),
        "exigencias": [{"id": e["id"], "rotulo": e["rotulo"], "assunto": e["assunto"],
                        "defeito": e["defeito"], "campos": e.get("campos", []),
                        "revisado": bool(e.get("revisado")),
                        "impossibilidade": bool(e.get("impossibilidade")),
                        "precedentes": len(e.get("precedentes", [])),
                        "fundamentos": len(e.get("fundamentos", []))}
                       for e in exigencias],
    }


_artigos = None


def indice_artigos():
    """Indice das normas, carregado uma vez e mantido em memoria."""
    global _artigos
    if _artigos is None:
        p = BASE / "dados" / "artigos.json"
        _artigos = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _artigos


def legislacao(r):
    """As normas cadastradas, com o que cada uma sustenta no catalogo."""
    normas = json.loads((BASE / "dados" / "normas.json").read_text(encoding="utf-8"))["normas"]
    idx = indice_artigos()

    saida = []
    for n in normas:
        pdf = BASE / "Fundamentações" / (n["fonte"] + ".pdf")
        saida.append({
            "id": n["id"], "nome": n["nome"], "referencia": n.get("referencia", ""),
            "esfera": n.get("esfera", ""), "arquivo": n["fonte"] + ".pdf",
            # No Vercel os PDFs nao sao enviados: so o indice ja extraido deles.
            "tem_pdf": True if SOMENTE_LEITURA else pdf.is_file(),
            "artigos": len(idx.get(n["id"], [])),
        })
    saida.sort(key=lambda x: x["nome"])
    return saida


def procura_artigos(norma, termo, limite=25):
    """Busca por numero de artigo ou por palavras no texto."""
    idx = indice_artigos()
    termo = (termo or "").strip()
    lista = idx.get(norma, [])
    if not termo:
        return [{"artigo": a["artigo"], "texto": a["texto"][:400]} for a in lista[:limite]]

    numero = re.fullmatch(r"(?:art\.?\s*)?(\d{1,4}(?:\s*-\s*[A-Za-z]{1,3})?)", termo, re.I)
    if numero:
        alvo = "art. " + re.sub(r"\s*-\s*", "-", numero.group(1)).upper()
        achados = [a for a in lista if a["artigo"].lower() == alvo.lower()]
        achados += [a for a in lista
                    if a["artigo"].lower().startswith(alvo.lower()) and a not in achados]
        return [{"artigo": a["artigo"], "texto": a["texto"][:1500]} for a in achados[:limite]]

    palavras = [sem_acento(p) for p in termo.split() if len(p) > 2]
    pontuados = []
    for a in lista:
        t = sem_acento(a["texto"])
        presentes = [p for p in palavras if p in t]
        if presentes:
            pontuados.append((len(presentes), -min(t.index(p) for p in presentes), a))
    pontuados.sort(key=lambda x: (-x[0], -x[1]))
    return [{"artigo": a["artigo"], "texto": a["texto"][:600]} for _, _, a in pontuados[:limite]]


def revisao(r):
    """Cada exigencia com o texto que ela produz e os artigos que cita.

    O texto sai preenchido com os exemplos de cada campo, para o registrador ler
    a exigencia inteira - e nao um esqueleto cheio de chaves.
    """
    cru = json.loads((BASE / "dados" / "exigencias.json").read_text(encoding="utf-8"))
    exemplos = {c: v.get("exemplo", c) for c, v in cru.get("campos", {}).items()}

    saida = []
    for e in sorted(r.cat.exigencias.values(), key=lambda x: (x["assunto"], x["rotulo"])):
        valores = {c: exemplos.get(c, c) for c in e.get("campos", [])}
        blocos = r._exigencia(Item(e["id"], valores), 1)
        texto = "".join(
            (f"<strong><u>{t}</u></strong>" if "negrito" in m else t)
            for t, m in blocos[0].partes)

        fundamentos = []
        for f in e.get("fundamentos", []):
            fundamentos.append({
                "norma": r.cat.nome_norma(f["norma"]),
                "artigo": f["artigo"],
                "texto": r.cat.texto_dispositivo(f["norma"], f["artigo"], f.get("partes")),
            })
        precedentes = [{"identificacao": r.cat.precedente(x)["identificacao"],
                        "tipo": r.cat.precedente(x)["tipo"],
                        "texto": r.cat.precedente(x)["texto"],
                        "fonte": r.cat.precedente(x)["fonte"]}
                       for x in e.get("precedentes", [])]
        saida.append({"id": e["id"], "rotulo": e["rotulo"], "texto": texto,
                      "revisado": bool(e.get("revisado")), "fundamentos": fundamentos,
                      "precedentes": precedentes,
                      "impossibilidade": bool(e.get("impossibilidade")),
                      "pendente": e.get("fundamentacao_pendente")})
    return saida


def marca_revisado(redator, eid, revisado):
    """Grava a validacao no catalogo e recarrega o que esta em memoria."""
    p = BASE / "dados" / "exigencias.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    achou = False
    for e in d["exigencias"]:
        if e["id"] == eid:
            e["revisado"] = bool(revisado)
            achou = True
    if not achou:
        return False
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    redator.cat.exigencias[eid]["revisado"] = bool(revisado)
    return True


def nome_arquivo(protocolo, especie):
    base = f"{protocolo} - " if protocolo else ""
    return f"{base}{especie.capitalize()}.docx".replace("/", "-")


class Manipulador(BaseHTTPRequestHandler):
    redator = None

    def log_message(self, *a):
        pass                      # o console fica limpo para o usuario

    # ------------------------------------------------------------------ envio

    def _envia(self, corpo, tipo="application/json; charset=utf-8", codigo=200):
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        elif isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    # ------------------------------------------------------------------- rotas

    def do_GET(self):
        caminho = self.path.split("?")[0].lstrip("/") or "index.html"
        if caminho == "api/catalogo":
            return self._envia(catalogo_para_tela(self.redator))
        if caminho == "api/revisao":
            return self._envia(revisao(self.redator))
        if caminho == "api/legislacao":
            return self._envia(legislacao(self.redator))
        if caminho == "api/artigos":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self._envia(procura_artigos(q.get("norma", [""])[0],
                                               q.get("q", [""])[0]))

        arquivo = (WEB / caminho).resolve()
        if not arquivo.is_file() or WEB.resolve() not in arquivo.parents:
            return self._envia({"erro": "não encontrado"}, codigo=404)
        self._envia(arquivo.read_bytes(),
                    TIPOS.get(arquivo.suffix, "application/octet-stream"))

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        dados = json.loads(self.rfile.read(tamanho) or b"{}")

        if self.path.strip("/") == "api/abrir-pasta":
            if SOMENTE_LEITURA:
                return self._envia({"ok": False, "erro": "sem pasta local"})
            alvo = Path(dados.get("caminho", ""))
            if alvo.exists():
                subprocess.Popen(["explorer", "/select,", str(alvo)])
            return self._envia({"ok": True})

        if self.path.strip("/") == "api/revisar":
            if SOMENTE_LEITURA:
                return self._envia({"ok": False, "erro":
                                    "a validação grava no catálogo e só funciona na "
                                    "instalação do cartório, onde o arquivo é gravável"})
            ok = marca_revisado(self.redator, dados.get("id"), dados.get("revisado"))
            return self._envia({"ok": ok})

        if self.path.strip("/") != "api/gerar":
            return self._envia({"erro": "rota desconhecida"}, codigo=404)

        itens = [Item(i["exigencia"], i.get("valores", {})) for i in dados["itens"]]
        try:
            blocos = self.redator.redige(dados["especie"], dados["titulo"], itens,
                                         judicial=dados.get("judicial", False))
        except (ValueError, KeyError) as erro:
            return self._envia({"ok": False, "erro": str(erro)})

        nome = nome_arquivo(dados.get("protocolo", ""), dados["especie"])
        resposta = {"ok": True, "arquivo": nome,
                    "nao_revisadas": self.redator.nao_revisadas(itens)}

        if SOMENTE_LEITURA:
            # Sem disco para gravar: a nota volta embutida na resposta e o
            # navegador a salva onde o usuario quiser.
            with tempfile.TemporaryDirectory() as tmp:
                destino = Path(tmp) / nome
                documento.grava(blocos, MOLDE, destino)
                resposta["conteudo"] = base64.b64encode(destino.read_bytes()).decode()
        else:
            SAIDA.mkdir(exist_ok=True)
            destino = SAIDA / nome
            documento.grava(blocos, MOLDE, destino)
            resposta["caminho"] = str(destino)

        self._envia(resposta)


def main():
    if not MOLDE.is_file():
        raise SystemExit(f"molde de formatação ausente: {MOLDE}")
    Manipulador.redator = Redator()

    # Porta sorteada pelo sistema, salvo se PORTA_NOTA pedir uma fixa.
    servidor = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORTA_NOTA", 0))),
                                   Manipulador)
    porta = servidor.server_address[1]
    endereco = f"http://127.0.0.1:{porta}/"
    print(f"Nota devolutiva rodando em {endereco}")
    print("Feche esta janela para encerrar.")
    threading.Timer(0.4, lambda: webbrowser.open(endereco)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
