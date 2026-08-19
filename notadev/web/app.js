// Tela da nota devolutiva. Conversa com o servidor local em notadev/servidor.py.
'use strict';

let CAT = null;                    // catalogo vindo do servidor
const marcadas = new Set();
const valores = new Map();         // "exigencia|campo" -> texto digitado

const $ = (id) => document.getElementById(id);

async function iniciar() {
  const r = await fetch('api/catalogo');
  CAT = await r.json();

  for (const e of CAT.especies) {
    const o = document.createElement('option');
    o.value = e.id; o.textContent = e.rotulo;
    $('especie').appendChild(o);
  }
  desenhaLista();
  desenhaCampos();

  $('filtro').addEventListener('input', desenhaLista);
  $('gerar').addEventListener('click', gerar);
  $('modal-fechar').addEventListener('click', () => $('modal').hidden = true);
}

function desenhaLista() {
  const termo = $('filtro').value.trim().toLowerCase();
  const lista = $('lista');
  lista.textContent = '';

  const visiveis = CAT.exigencias.filter(e =>
    !termo || (e.rotulo + ' ' + e.assunto + ' ' + e.defeito).toLowerCase().includes(termo));

  if (!visiveis.length) {
    lista.innerHTML = '<div class="vazio">Nenhuma pendência com esse termo.</div>';
    return;
  }

  for (const e of visiveis) {
    const div = document.createElement('label');
    div.className = 'item' + (marcadas.has(e.id) ? ' marcado' : '');

    const cx = document.createElement('input');
    cx.type = 'checkbox';
    cx.checked = marcadas.has(e.id);
    cx.addEventListener('change', () => {
      cx.checked ? marcadas.add(e.id) : marcadas.delete(e.id);
      div.classList.toggle('marcado', cx.checked);
      desenhaCampos();
      atualizaContagem();
    });

    const texto = document.createElement('div');
    const nome = document.createElement('div');
    nome.className = 'nome';
    nome.textContent = e.rotulo;
    const meta = document.createElement('div');
    meta.className = 'meta';
    if (!e.revisado) {
      const p = document.createElement('span');
      p.className = 'pilula';
      p.textContent = 'não revisada';
      meta.append(p);
    }
    if (!e.fundamentos && !e.precedentes) {
      const p = document.createElement('span');
      p.className = 'pilula';
      p.textContent = 'sem lei citada';
      meta.append(p);
    }
    if (e.impossibilidade) {
      const p = document.createElement('span');
      p.className = 'pilula impossivel';
      p.textContent = 'devolve o título';
      meta.append(p);
    }
    texto.append(nome);
    if (meta.childElementCount) texto.append(meta);
    div.append(cx, texto);
    lista.append(div);
  }
}

function desenhaCampos() {
  const alvo = $('campos');
  alvo.textContent = '';

  if (!marcadas.size) {
    alvo.innerHTML = '<div class="vazio">Marque as pendências ao lado.</div>';
    return;
  }

  for (const e of CAT.exigencias.filter(x => marcadas.has(x.id))) {
    const g = document.createElement('div');
    g.className = 'grupo';
    const h = document.createElement('h3');
    h.textContent = e.rotulo;
    g.append(h);

    if (!e.campos.length) {
      const p = document.createElement('div');
      p.className = 'nada';
      p.textContent = 'Não pede nenhum dado.';
      g.append(p);
    }

    for (const c of e.campos) {
      const info = CAT.campos[c] || {};
      const linha = document.createElement('div');
      linha.className = 'linha';

      const lab = document.createElement('label');
      lab.textContent = info.rotulo || c;
      // campo com 'padrao' é opcional: em branco, entra a redação genérica
      if (info.padrao) {
        const op = document.createElement('span');
        op.className = 'opcional';
        op.textContent = ' (opcional)';
        lab.append(op);
      }
      const inp = document.createElement('input');
      inp.value = valores.get(e.id + '|' + c) || '';
      inp.placeholder = info.exemplo || '';
      if (info.padrao) inp.title = `Em branco, a nota diz: "${info.padrao}"`;
      inp.addEventListener('input', () => valores.set(e.id + '|' + c, inp.value));

      linha.append(lab, inp);
      g.append(linha);
    }
    alvo.append(g);
  }
}

function atualizaContagem() {
  const n = marcadas.size;
  const naoRevisadas = CAT.exigencias.filter(e => marcadas.has(e.id) && !e.revisado).length;
  $('contagem').textContent = n
    ? `${n} pendência${n > 1 ? 's' : ''} marcada${n > 1 ? 's' : ''}`
    : 'nenhuma pendência marcada';
  $('aviso').textContent = naoRevisadas
    ? `${naoRevisadas} com fundamentação ainda não revisada por registrador`
    : '';
}

function avisa(titulo, html, caminho) {
  $('modal-titulo').textContent = titulo;
  $('modal-corpo').innerHTML = html;
  const b = $('modal-pasta');
  b.hidden = !caminho;
  b.onclick = () => fetch('api/abrir-pasta', {
    method: 'POST', body: JSON.stringify({ caminho }),
  });
  $('modal').hidden = false;
}

async function gerar() {
  if (!marcadas.size) return avisa('Nota vazia', '<p>Marque ao menos uma pendência.</p>');
  if (!$('titulo').value.trim())
    return avisa('Falta o título', '<p>Informe o título apresentado — ele entra no preâmbulo.</p>');

  const itens = [...marcadas].map(id => {
    const e = CAT.exigencias.find(x => x.id === id);
    const v = {};
    for (const c of e.campos) v[c] = (valores.get(id + '|' + c) || '').trim();
    return { exigencia: id, valores: v };
  });

  $('gerar').disabled = true;
  try {
    const r = await fetch('api/gerar', {
      method: 'POST',
      body: JSON.stringify({
        especie: $('especie').value,
        titulo: $('titulo').value.trim(),
        protocolo: $('protocolo').value.trim(),
        judicial: $('judicial').checked,
        itens,
      }),
    });
    const res = await r.json();
    if (!res.ok) return avisa('Falta preencher', `<p>${res.erro}</p>`);

    let html = `<p>Nota gravada em:</p><div class="caminho">${res.caminho}</div>`;
    if (res.nao_revisadas.length) {
      html += '<p><strong>Fundamentação ainda não revisada por registrador:</strong></p><ul>'
            + res.nao_revisadas.map(x => `<li>${x}</li>`).join('') + '</ul>'
            + '<p>Confira os artigos citados antes de expedir.</p>';
    }
    avisa('Nota gerada', html, res.caminho);
  } finally {
    $('gerar').disabled = false;
  }
}

iniciar();
