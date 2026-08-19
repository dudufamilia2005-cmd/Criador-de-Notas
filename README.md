# Criador de Notas

Gera notas devolutivas e de exigência do Registro de Imóveis, com o texto e a
fundamentação legal prontos, no formato usado pelo Cartório do 1º Ofício de
Morrinhos/GO.

O escrevente marca as pendências que encontrou na qualificação, preenche os
dados de cada uma e recebe um `.docx` formatado, com cada exigência seguida dos
artigos que a sustentam — transcritos do texto oficial da norma.

## Como funciona

O catálogo tem **33 exigências**, cada uma com três partes: o defeito, a
providência e os dispositivos legais. A nota se monta assim:

> `Verifica-se que <defeito>.` **`Dessa forma, faz-se necessária`** `<providência>, <fecho>.`

Abaixo de cada exigência entram os artigos citados, em corpo menor e recuados.

A fundamentação **não é digitada à mão nem copiada de notas antigas**: as 23
normas da pasta `Fundamentações` são lidas e quebradas em artigos (7.084 no
total), e o catálogo aponta qual artigo — e qual parágrafo, inciso ou alínea —
deve ser transcrito. Trocar o PDF por uma versão mais nova atualiza o texto de
todas as notas.

## Rodando

Requer Python 3.12 ou mais novo. Não há dependência além do `pypdf`, usado só
para extrair o texto dos PDFs das normas.

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install pypdf
.venv\Scripts\python.exe ferramentas\indexa_normas.py
.venv\Scripts\python.exe ferramentas\monta_dispositivos.py
```

Depois disso, `Nota devolutiva.bat` abre a ferramenta no navegador. Ela sobe um
servidor local em `127.0.0.1`, numa porta sorteada — nada fica exposto na rede.

Três telas:

- **Nota devolutiva** — marcar pendências, preencher, gerar o documento.
- **Legislação** — as normas cadastradas e a consulta a qualquer artigo, por
  número ou por assunto.
- **Revisão da fundamentação** — onde um registrador confere se o artigo citado
  sustenta mesmo a exigência, e valida.

## Acrescentando uma norma

Salve o PDF em `Fundamentações`, escreva a entrada em `dados/normas.json` e rode
`indexa_normas.py`. Para achar o artigo pertinente a uma exigência nova:

```
.venv\Scripts\python.exe ferramentas\busca_artigo.py usufruto extinção --norma CNPFE-GO
```

## O que este projeto não faz

**Não inventa fundamentação.** Nenhum artigo entra numa nota sem casar com o PDF
da norma; `ferramentas/valida_catalogo.py` reprova o catálogo se algum não
conferir. Quando não há dispositivo pertinente nas normas cadastradas, a
exigência sai sem lei citada, com o motivo escrito — nunca com um artigo
plausível.

**Não substitui o registrador.** Os artigos foram escolhidos lendo a lei, mas
a pertinência de cada um a cada exigência é juízo de quem tem competência para
isso. Enquanto uma exigência não for validada na tela de revisão, toda nota que
a use sai marcada como fundamentação não revisada.

## Estrutura

| Pasta | |
|---|---|
| `dados/` | normas, dispositivos, exigências, preâmbulos — editáveis sem programar |
| `notadev/` | catálogo, redator, gerador de `.docx` e o servidor da interface |
| `ferramentas/` | indexação das normas, busca de artigos e validação do catálogo |
| `modelo/` | molde de formatação: papel, margens e estilos |
| `Fundamentações/` | os PDFs das normas |

O `.docx` é gerado com `zipfile` e `xml.etree` da biblioteca padrão — um `.docx`
é um zip de XML. O molde fornece papel, margens e estilos; o conteúdo é escrito
por cima.
