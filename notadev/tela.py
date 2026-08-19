# -*- coding: utf-8 -*-
"""Tela de preenchimento da nota devolutiva.

Tkinter da biblioteca padrao: sem dependencia, funciona offline e abre com
duplo clique no atalho. O escrevente marca as pendencias que encontrou,
preenche os dados de cada uma e gera o .docx.
"""
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import documento
from .catalogo import BASE
from .redator import Item, Redator

MOLDE = BASE / "modelo" / "molde-nota.docx"


class Tela:
    def __init__(self, raiz):
        self.raiz = raiz
        self.redator = Redator()
        self.cat = self.redator.cat
        cru = json.loads((BASE / "dados" / "exigencias.json").read_text(encoding="utf-8"))
        self.rotulos = cru.get("campos", {})

        raiz.title("Nota devolutiva - 1º Ofício de Morrinhos/GO")
        raiz.geometry("1180x760")
        raiz.minsize(980, 620)

        self.marcadas = {}      # id -> BooleanVar
        self.entradas = {}      # (id, campo) -> Entry

        self._cabecalho()
        self._corpo()
        self._rodape()
        self._atualiza_campos()

    # ------------------------------------------------------------- cabecalho

    def _cabecalho(self):
        f = ttk.LabelFrame(self.raiz, text="Dados da nota", padding=8)
        f.pack(fill="x", padx=10, pady=(10, 4))

        ttk.Label(f, text="Espécie:").grid(row=0, column=0, sticky="w")
        self.especie = ttk.Combobox(f, state="readonly", width=22,
                                    values=list(self.redator.modelo["especies"]))
        self.especie.current(0)
        self.especie.grid(row=0, column=1, sticky="w", padx=(4, 18))

        self.judicial = tk.BooleanVar()
        ttk.Checkbutton(f, text="Título judicial (acrescenta o parágrafo sobre "
                                "qualificação de título judicial)",
                        variable=self.judicial).grid(row=0, column=2, sticky="w")

        ttk.Label(f, text="Título apresentado:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.titulo = ttk.Entry(f)
        self.titulo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(8, 0), padx=(4, 0))
        f.columnconfigure(2, weight=1)

    # ----------------------------------------------------------------- corpo

    def _corpo(self):
        painel = ttk.Panedwindow(self.raiz, orient="horizontal")
        painel.pack(fill="both", expand=True, padx=10, pady=4)

        esq = ttk.LabelFrame(painel, text="Pendências encontradas", padding=6)
        painel.add(esq, weight=1)

        busca = ttk.Frame(esq)
        busca.pack(fill="x", pady=(0, 6))
        ttk.Label(busca, text="Filtrar:").pack(side="left")
        self.filtro = ttk.Entry(busca)
        self.filtro.pack(side="left", fill="x", expand=True, padx=4)
        self.filtro.bind("<KeyRelease>", lambda _: self._desenha_lista())

        self.lista = self._rolavel(esq)

        dir_ = ttk.LabelFrame(painel, text="Dados de cada exigência", padding=6)
        painel.add(dir_, weight=1)
        self.campos = self._rolavel(dir_)

        self._desenha_lista()

    def _rolavel(self, pai):
        """Area com barra de rolagem. Devolve o frame onde se desenha."""
        tela = tk.Canvas(pai, highlightthickness=0)
        barra = ttk.Scrollbar(pai, orient="vertical", command=tela.yview)
        dentro = ttk.Frame(tela)
        dentro.bind("<Configure>",
                    lambda _: tela.configure(scrollregion=tela.bbox("all")))
        janela = tela.create_window((0, 0), window=dentro, anchor="nw")
        tela.bind("<Configure>", lambda e: tela.itemconfigure(janela, width=e.width))
        tela.configure(yscrollcommand=barra.set)
        tela.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        tela.bind_all("<MouseWheel>",
                      lambda e: tela.yview_scroll(-int(e.delta / 120), "units"))
        return dentro

    def _desenha_lista(self):
        for w in self.lista.winfo_children():
            w.destroy()
        termo = self.filtro.get().strip().lower()
        for eid, e in sorted(self.cat.exigencias.items(),
                             key=lambda kv: (kv[1]["assunto"], kv[1]["rotulo"])):
            alvo = (e["rotulo"] + " " + eid + " " + e["defeito"]).lower()
            if termo and termo not in alvo:
                continue
            var = self.marcadas.setdefault(eid, tk.BooleanVar())
            linha = ttk.Frame(self.lista)
            linha.pack(fill="x", pady=1)
            ttk.Checkbutton(linha, text=e["rotulo"], variable=var,
                            command=self._atualiza_campos).pack(side="left", anchor="w")
            if not e.get("revisado"):
                ttk.Label(linha, text="não revisada",
                          foreground="#777").pack(side="right")

    def _selecionadas(self):
        return [eid for eid, v in self.marcadas.items() if v.get()]

    def _atualiza_campos(self):
        anteriores = {k: w.get() for k, w in self.entradas.items()}
        for w in self.campos.winfo_children():
            w.destroy()
        self.entradas.clear()

        escolhidas = self._selecionadas()
        if not escolhidas:
            ttk.Label(self.campos, foreground="#777",
                      text="Marque as pendências à esquerda.").pack(anchor="w", pady=8)
            self._conta()
            return

        for eid in escolhidas:
            e = self.cat.exigencia(eid)
            cx = ttk.LabelFrame(self.campos, text=e["rotulo"], padding=6)
            cx.pack(fill="x", pady=4)
            if not e.get("campos"):
                ttk.Label(cx, foreground="#777",
                          text="Não pede nenhum dado.").pack(anchor="w")
            for c in e.get("campos", []):
                r = self.rotulos.get(c, {})
                linha = ttk.Frame(cx)
                linha.pack(fill="x", pady=2)
                ttk.Label(linha, text=r.get("rotulo", c) + ":", width=26,
                          anchor="w").pack(side="left")
                ent = ttk.Entry(linha)
                ent.pack(side="left", fill="x", expand=True)
                if (eid, c) in anteriores:
                    ent.insert(0, anteriores[(eid, c)])
                exemplo = r.get("exemplo")
                if exemplo:
                    ttk.Label(linha, text=f"ex.: {exemplo}", foreground="#999",
                              width=32, anchor="w").pack(side="left", padx=(6, 0))
                self.entradas[(eid, c)] = ent
        self._conta()

    # ---------------------------------------------------------------- rodape

    def _rodape(self):
        f = ttk.Frame(self.raiz, padding=(10, 6))
        f.pack(fill="x")
        self.status = ttk.Label(f, text="", foreground="#a05000")
        self.status.pack(side="left")
        ttk.Button(f, text="Gerar nota…", command=self.gerar).pack(side="right")

    def _conta(self):
        escolhidas = self._selecionadas()
        pend = self.redator.nao_revisadas([Item(x) for x in escolhidas])
        if pend:
            self.status.config(
                text=f"{len(escolhidas)} exigência(s) · {len(pend)} com fundamentação "
                     f"ainda não revisada por registrador")
        else:
            self.status.config(text=f"{len(escolhidas)} exigência(s)")

    # ----------------------------------------------------------------- gerar

    def gerar(self):
        escolhidas = self._selecionadas()
        if not escolhidas:
            messagebox.showwarning("Nota vazia", "Marque ao menos uma pendência.")
            return
        titulo = self.titulo.get().strip()
        if not titulo:
            messagebox.showwarning("Falta o título",
                                   "Informe o título apresentado — ele entra no preâmbulo.")
            return

        itens = [Item(eid, {c: w.get().strip()
                            for (i, c), w in self.entradas.items() if i == eid})
                 for eid in escolhidas]
        try:
            blocos = self.redator.redige(self.especie.get(), titulo, itens,
                                         judicial=self.judicial.get())
        except (ValueError, KeyError) as erro:
            messagebox.showerror("Falta preencher", str(erro))
            return

        if not MOLDE.is_file():
            messagebox.showerror(
                "Molde ausente",
                f"O molde de formatação não está em:\n{MOLDE}\n\n"
                "Ele é uma nota real do cartório, de onde saem papel, margens e estilos.")
            return

        destino = filedialog.asksaveasfilename(
            defaultextension=".docx", filetypes=[("Documento do Word", "*.docx")],
            initialfile="nota.docx", title="Salvar a nota")
        if not destino:
            return
        try:
            documento.grava(blocos, MOLDE, destino)
        except OSError as erro:
            messagebox.showerror("Não foi possível salvar", str(erro))
            return

        pend = self.redator.nao_revisadas(itens)
        recado = f"Nota gravada em:\n{destino}"
        if pend:
            recado += ("\n\nATENÇÃO: a fundamentação destas exigências ainda não foi "
                       "revisada por registrador:\n· " + "\n· ".join(pend) +
                       "\n\nConfira os artigos citados antes de expedir.")
        messagebox.showinfo("Nota gerada", recado)


def main():
    raiz = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    Tela(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
