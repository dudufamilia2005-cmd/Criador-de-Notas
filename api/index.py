# -*- coding: utf-8 -*-
"""Ponto de entrada da implantação no Vercel.

O Vercel executa funções, não um servidor de longa duração: cada requisição
chega isolada e o disco é somente leitura. Este arquivo reaproveita o mesmo
manipulador usado na máquina do cartório (notadev/servidor.py) e só resolve as
diferenças de ambiente:

  - a raiz do projeto não está no caminho de importação;
  - a reescrita do vercel.json entrega o caminho original em self.path, mas
    convém tolerar o prefixo da função;
  - as rotas que gravam ficam desligadas, pelo SOMENTE_LEITURA de lá.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from notadev.servidor import Manipulador, Redator          # noqa: E402

Manipulador.redator = Redator()


class handler(Manipulador):
    """O Vercel procura por uma classe chamada 'handler'."""

    def _normaliza(self):
        if self.path.startswith("/api/index"):
            self.path = self.path[len("/api/index"):] or "/"

    def do_GET(self):
        self._normaliza()
        super().do_GET()

    def do_POST(self):
        self._normaliza()
        super().do_POST()
