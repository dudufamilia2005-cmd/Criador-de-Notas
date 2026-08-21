# Gerador de notas devolutivas

Ferramenta do Cartório do 1º Ofício de Morrinhos/GO para redigir notas
devolutivas e de exigência do Registro de Imóveis, com fundamentação legal
conferida contra a norma de origem.

## Ambiente

Python 3.15.0rc1 em `%LOCALAPPDATA%\Programs\Python\Python315`, venv em `.venv`.

Por ser uma *release candidate*, pacotes que compilam C não instalam: `lxml` —
e portanto `python-docx` — falham por falta do MSVC. **Não introduza essas
dependências.** Leitura e escrita de `.docx` são feitas com `zipfile` +
`xml.etree` da biblioteca padrão, o que basta: `.docx` é um zip de XML.
Única dependência instalada: `pypdf`, só para extrair texto das normas.

## Como rodar

```
.venv\Scripts\python.exe ferramentas\valida_catalogo.py
```

Roda antes de confiar em qualquer nota gerada. Reprova o catálogo se algum
fundamento não conferir com a fonte.

```
.venv\Scripts\python.exe ferramentas	esta_redator.py
```

Regressão do recorte do artigo: o que o redator apaga do texto da lei. Cada
caso ali é um estrago que já aconteceu — ou que quase passou.

Depois de acrescentar uma norma, ou de mexer nos fundamentos do catálogo:

```
.venv\Scripts\python.exe ferramentas\indexa_normas.py
.venv\Scripts\python.exe ferramentas\monta_dispositivos.py
```

O primeiro relê os PDFs das normas e os quebra em artigos; o segundo traz para o
catálogo o texto oficial dos artigos citados.

Para achar o artigo pertinente a uma exigência nova, lendo a lei:

```
.venv\Scripts\python.exe ferramentas\busca_artigo.py usufruto extinção --norma CNPFE-GO
```

## Fonte da verdade

- `Fundamentações\*.pdf` — texto oficial das normas. Manda sobre a redação de
  qualquer artigo. Acrescentar norma = salvar o PDF ali e escrever a entrada em
  `dados\normas.json`.
- O acervo de notas do cartório serviu, uma única vez, para aprender a forma da
  nota: formatação, vocabulário, preâmbulos e fechos. **Não é fonte de nada em
  produção** — o sistema não o lê, o catálogo não o referencia, e nenhum arquivo
  em `dados\` guarda contagem ou citação dele. As ferramentas de levantamento
  continuam no repositório apenas como registro de como o estudo foi feito.
- `.cache-texto\` — texto extraído dos PDFs. Artefato gerado, descartável.
- `dados/artigos.json` — o índice das leis. Também é gerado, mas **é
  versionado**: sem ele a implantação no Vercel não tem o que consultar, e os
  PDFs ficam de fora de lá por peso.

## Invariantes

1. **A lei é a única fonte da fundamentação.** `indexa_normas.py` quebra cada PDF
   em artigos e `monta_dispositivos.py` traz o texto oficial para o catálogo.
   Nada de texto legal vem de nota antiga. Artigo trocado numa nota é problema do
   cartório perante a Corregedoria: o custo do erro não é simétrico.

1-A. **Compilado traz redação revogada.** O PDF goiano repete o código inteiro,
   uma vez por versão histórica; o índice fica com a última redação não marcada
   como vencida. Sem isso o art. 77 do CTE-GO saía com o texto que valeu até
   31.12.2000. Ver `REDACAO_VENCIDA` em `indexa_normas.py`.

1-B. **Artigo longo é citado por recorte.** O art. 176 da Lei 6.015 tem oito mil
   caracteres. O catálogo aponta quais `partes` citar; sai o caput e os trechos
   pedidos, separados por `(...)`. Rótulo repetido ganha ordinal — o art. 440-AQ
   tem três alíneas `a)`.
2. **Artigo escolhido não é artigo validado.** Os fundamentos foram escolhidos
   lendo a lei — `ferramentas/busca_artigo.py` procura no texto indexado —, mas
   quem decide se o dispositivo é pertinente àquela exigência é registrador.
   Enquanto `revisado` for `false`, a nota sai marcada como fundamentação não
   revisada.
3. **Sem artigo pertinente, a exigência sai sem lei citada**, com o motivo
   escrito em `fundamentacao_pendente`. Hoje é o caso do selo eletrônico.
   Citar dispositivo plausível seria pior do que não citar nenhum.
3-A. **Norma nova pode desmentir o texto da exigência.** O art. 211-A do
   CNPFE-GO (Provimento 180, de 26/03/2026), § 1º, diz que é *irrelevante*
   para o desconto de 50% possuir imóvel anterior adquirido fora do SFH — e
   a exigência pedia declaração sobre exatamente isso. Ao acrescentar norma,
   reler as exigências do assunto, não só juntar a citação.
4. **A formatação sai do molde, não de código.** O `.docx` é gerado reescrevendo
   o conteúdo de uma nota real do cartório, preservando `styles.xml` e
   `numbering.xml` do arquivo original. Assim a formatação é idêntica por
   construção, e não por eu tentar reproduzi-la.
5. **O estilo é o discursivo fundamentado** (decisão da serventia, 18/08/2026):
   `Verifica-se que <defeito>.` + **`Dessa forma, faz-se necessária`** (negrito e
   sublinhado) + `<providência>, <fecho>.` A fórmula concorda com o que vem
   depois: "necessário o prévio registro", "necessária a apresentação".
6. **A cláusula de assinatura é fragmento, não texto repetido.** Cabe em quase
   toda exigência; mora uma vez em `fragmentos.assinatura`. O mesmo vale
   para o fecho e para o protocolo apartado.
6-A. **Dado que enriquece a frase vai entre colchetes.** `(CCIR)[ do imóvel da
   matrícula n.º {matricula}]` some inteiro quando o campo fica vazio, em vez de
   deixar buraco ou obrigar o escrevente a preencher. Campo usado só dentro de
   colchetes é opcional por construção — não precisa de `padrao`.
7-A. **O mesmo código roda local e no Vercel.** `SOMENTE_LEITURA` (variável de
   ambiente `VERCEL`) desliga o que grava: a validação da fundamentação e a
   gravação em `saida/`. Lá a nota volta em base64 e o navegador a baixa. Não
   crie um segundo caminho de código para a nuvem.
7. **O texto do artigo citado sai em Arial 9 recuado**, o corpo em Arial 10
   justificado com entrelinhas 1,5. São camadas visuais distintas, e é o que
   dá à nota a cara que ela tem hoje.

## Formatação da nota

Papel A4 21,59 × 27,94 cm; margens 2,54 sup/inf e 3,32 esq/dir. Sem cabeçalho
nem rodapé no arquivo. Corpo: Arial 10, justificado, entrelinhas 1,5, recuo de
1ª linha 1,25 cm. Exigência: lista automática, recuo deslocado, 5 pt antes.
Fundamentação: Arial 9, recuo esquerdo 3,75–4,00 cm, entrelinhas 1,0.

## Pendências conhecidas

- Provimento CNJ 161/2024: o PDF não tem texto extraível — traz só índices de
  glifos. Precisa de OCR ou de outra cópia. Nenhuma exigência o usa hoje.
- Nenhuma das 65 exigências foi revisada por registrador: todas saem com aviso.
- `notadev/tela.py` é a interface antiga, em Tkinter, mantida até a nova ser
  aprovada. Quem roda pelo `.bat` é `notadev/servidor.py`, servida no navegador.
- Não definido ainda: se a nota é impressa em papel timbrado ou se o sistema
  deve gerar cabeçalho e assinatura; e de onde vêm os dados variáveis do
  preâmbulo (protocolo, apresentante, tipo de título).
