# Gerador de notas devolutivas

Ferramenta do Cartório do 1º Ofício de Morrinhos/GO para redigir notas
devolutivas e de exigência do Registro de Imóveis, com fundamentação legal
conferida contra a norma de origem.

## Ambiente

Python 3.14 em `%LOCALAPPDATA%\Programs\Python\Python314`, venv em `.venv`.
Única dependência: `pypdf`, só para extrair texto das normas — fixada em
`requirements.txt`. Todo o resto é biblioteca padrão.

Para refazer o ambiente:

```
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Não introduza `python-docx` nem outra dependência para escrever o .docx.**
Até 24/08/2026 a razão era outra: sob a 3.15.0rc1 o `lxml` não tinha wheel e não
compilava sem o MSVC. Na 3.14 ele instala normalmente — o impedimento acabou, e
a regra continua por escolha, não por impossibilidade: a escrita com `zipfile` +
`xml.etree` já funciona, e é ela que garante a formatação idêntica por
construção (invariante 4), copiando as peças do molde em vez de reproduzi-las.
Trocar isso seria reescrever o que funciona e assumir peso a mais no Vercel.
Se um dia compensar, é decisão da serventia — não um detalhe de implementação.

## Como rodar

```
.venv\Scripts\python.exe ferramentas\valida_catalogo.py
```

Roda antes de confiar em qualquer nota gerada. Reprova o catálogo se algum
fundamento não conferir com a fonte.

```
.venv\Scripts\python.exe ferramentas\testa_redator.py
```

Regressão do recorte do artigo: o que o redator apaga do texto da lei. Cada
caso ali é um estrago que já aconteceu — ou que quase passou.

Depois de acrescentar uma norma, ou de mexer nos fundamentos do catálogo:

```
.venv\Scripts\python.exe ferramentas\extrai_texto.py
.venv\Scripts\python.exe ferramentas\indexa_normas.py
.venv\Scripts\python.exe ferramentas\monta_dispositivos.py
```

São três passos, nesta ordem: o primeiro lê os PDFs e grava o texto em
`.cache-texto/`; o segundo quebra esse texto em artigos; o terceiro traz para o
catálogo o texto oficial dos artigos citados. `extrai_texto.py` pula o que já
está em dia com o PDF — na prática só a norma nova é lida.

Até 24/08/2026 o primeiro passo **não existia no repositório**: a extração era
feita à mão, em script solto. Como `.cache-texto/` é descartável e ignorado pelo
git, apagá-lo deixava o índice sem como ser refeito — e `indexa_normas.py` não
reclamava: anotava `SEM TEXTO EXTRAIDO` e seguia, entregando um índice a menos
uma lei inteira.

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
- **Nem todo PDF em `Fundamentações\` é norma cadastrada.** Ali também ficam as
  peças de jurisprudência (fonte dos precedentes) e atos que já foram absorvidos
  por um texto consolidado. `Provimento  195.pdf` é o segundo caso: ele altera o
  CNN, e a nossa cópia do CNN já vem consolidada — cita o próprio Provimento 195
  em 277 pontos, e vai até o Provimento 246. Conferido em 26/08/2026: dos 42
  artigos que ele toca, 35 já estão no índice e os 7 restantes são os artigos do
  próprio instrumento ("passa a vigorar com as seguintes alterações", "entra em
  vigor"). **Cadastrá-lo duplicaria cada regra** e abriria a porta para citar a
  redação de junho/2025 de um artigo que provimento posterior já mudou.
  `extrai_texto.py` percorre `dados
ormas.json`, então PDF não cadastrado é
  simplesmente ignorado — o arquivo fica como procedência, sem efeito.
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

1-F. **Qual das redações repetidas é a vigente depende do compilador.** O mesmo
   inciso aparece várias vezes, uma por redação histórica, e a ordem não significa
   a mesma coisa nos dois: no Planalto o **original vem primeiro, sem anotação**,
   e cada redação nova vem depois marcada `(Redação dada pela Lei nº …)` — vale a
   **última**; no código goiano a **anotada é a vigente e pode vir primeiro**, com
   a antiga impressa depois **sem marca nenhuma** (art. 352, inciso VII: 90 dias
   anotado antes, 30 dias sem marca depois). Por isso não há regra automática, e
   `esta_revogada` não pega esses casos. Ao recortar inciso repetido, **leia a
   anotação no texto bruto** antes de escolher.

1-G. **`(...)` afirma omissão — não use entre partes vizinhas.** `texto_dispositivo`
   consulta a ordem das partes no artigo e só separa com `(...)` o que tem buraco
   no meio. Antes marcava tudo, e a nota dizia que havia texto omitido onde o
   original é corrido.

1-C. **Revogação também vive dentro do artigo.** `1-A` cuidava do artigo
   inteiro; o parágrafo revogado passava. No art. 77 do CTE-GO, 12 das 15
   partes citáveis estavam revogadas — inclusive o § 5º, que a exigência do
   ITCD citava. Agora `monta_dispositivos.py` apura a revogação **no texto
   bruto**, antes de a limpeza apagar a prova, e separa as partes mortas em
   `revogadas`. São quatro sinais: o histórico do próprio código
   ("REVOGADO O § 5º DO ART. 77 PELO ART. 2º..."), a casca "§ 5º Revogado;",
   o "(Revogada pela Lei ...)" do Planalto e a vigência com data final.
   `valida_catalogo.py` reprova quem citar parte revogada, e
   `texto_dispositivo` se recusa a imprimi-la.

1-D. **Ordem importa: recortar e só depois limpar.** A quebra em partes depende
   da pontuação, e a anotação de tramitação termina em `)`. Limpando antes,
   273 das 571 partes deixavam de ser reconhecidas; limpando depois, a prova da
   revogação continua legível. Por isso `prepara()` tira só o que *atrapalha o
   corte* — rodapé de impressão, histórico em caixa alta, número de página
   solto — e a limpeza completa corre parte por parte.

1-B. **Artigo longo é citado por recorte.** O art. 176 da Lei 6.015 tem oito mil
   caracteres. O catálogo aponta quais `partes` citar; sai o caput e os trechos
   pedidos, separados por `(...)`. Rótulo repetido ganha ordinal — o art. 440-AQ
   tem três alíneas `a)`.
1-E. **Norma federal e código goiano lado a lado é reforço, não repetição a
   corrigir.** A pendência da hipoteca cita o art. 251 da Lei 6.015 e o art. 926
   do CNPFE-GO, que dizem quase a mesma frase — o código estadual reproduz a lei
   federal. Decisão da serventia (26/08/2026): fica, porque mostrar as duas
   fontes reforça a exigência perante o apresentante. Não "limpe" isso.

2. **Artigo escolhido não é artigo validado.** Os fundamentos foram escolhidos
   lendo a lei — `ferramentas/busca_artigo.py` procura no texto indexado —, mas
   quem decide se o dispositivo é pertinente àquela exigência é registrador.
   Enquanto `revisado` for `false`, a nota sai marcada como fundamentação não
   revisada.
3. **Sem artigo pertinente, a exigência sai sem lei citada**, com o motivo
   escrito em `fundamentacao_pendente`. Hoje nenhuma está nessa situação — a do
   selo eletrônico, que era o caso, passou a citar os arts. 109 e 109-A do
   CNPFE-GO.
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
7-B. **A prévia informa o erro com status 200.** Quando a montagem falha, o
   servidor devolve `{"html": "", "erro": "<motivo>"}` — e não um código HTTP de
   erro. Quem consome precisa mostrar esse `erro`: é por ele que chegam à tela a
   exigência que saiu do catálogo (aba antiga depois de um deploy) e a recusa de
   imprimir dispositivo revogado (invariante 1-C). Trocá-lo por um texto genérico
   deixa a recusa muda, e foi o que aconteceu uma vez.

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

- CTE-GO arts. 77-C e 102 constam revogados por inteiro; nenhuma exigência os
  cita. O art. 4º, § 4º, da Lei 19.191/2015 saiu da exigência do ITCD: ele vale,
  mas o seu inciso II diz que, acolhida a recomendação do oficial, *não* é devido
  recolhimento complementar de imposto estadual — o oposto do que a providência
  pede. **Retirada provisória, acordada com a serventia em 24/08/2026**; repor é
  decisão de registrador, e a omissão é escolha, não esquecimento.
- Provimento CNJ 161/2024: o PDF não tem texto extraível — traz só índices de
  glifos. Precisa de OCR ou de outra cópia. Nenhuma exigência o usa hoje.
- Nenhuma das 65 exigências foi revisada por registrador: todas saem com aviso.
- `notadev/tela.py` é a interface antiga, em Tkinter, mantida até a nova ser
  aprovada. Quem roda pelo `.bat` é `notadev/servidor.py`, servida no navegador.
- Não definido ainda: se a nota é impressa em papel timbrado ou se o sistema
  deve gerar cabeçalho e assinatura; e de onde vêm os dados variáveis do
  preâmbulo (protocolo, apresentante, tipo de título).
