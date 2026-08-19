// Tela de revisão: mostra o texto que cada exigência produz e os artigos que
// cita, com um botão para o registrador validar ou desfazer a validação.
'use strict';

const $ = (id) => document.getElementById(id);
let DADOS = [];

async function iniciar() {
  DADOS = await (await fetch('api/revisao')).json();
  desenha();
}

function desenha() {
  const lista = $('lista');
  lista.textContent = '';

  for (const e of DADOS) {
    const cx = document.createElement('section');
    cx.className = 'cartao revisao-item' + (e.revisado ? ' validada' : '');

    const cab = document.createElement('div');
    cab.className = 'cabeca';
    const h = document.createElement('h2');
    h.textContent = e.rotulo;
    const b = document.createElement('button');
    b.className = e.revisado ? 'secundario' : 'primario';
    b.textContent = e.revisado ? 'Validada — desfazer' : 'Validar fundamentação';
    b.onclick = () => alterna(e.id, !e.revisado, b);
    cab.append(h, b);

    const corpo = document.createElement('div');
    corpo.className = 'revisao-corpo';

    const p = document.createElement('p');
    p.className = 'texto-exigencia';
    p.innerHTML = e.texto;
    corpo.append(p);

    if (!e.fundamentos.length) {
      const s = document.createElement('div');
      s.className = 'sem-lei';
      s.textContent = e.pendente || 'Sem lei citada.';
      corpo.append(s);
    }

    let normaAtual = null;
    for (const f of e.fundamentos) {
      if (f.norma !== normaAtual) {
        const n = document.createElement('div');
        n.className = 'norma';
        n.textContent = f.norma;
        corpo.append(n);
        normaAtual = f.norma;
      }
      const a = document.createElement('div');
      a.className = 'artigo';
      const t = document.createElement('strong');
      t.textContent = f.artigo + '. ';
      a.append(t, document.createTextNode(f.texto));
      corpo.append(a);
    }

    cx.append(cab, corpo);
    lista.append(cx);
  }
  contar();
}

function contar() {
  const n = DADOS.filter(e => e.revisado).length;
  $('contagem').textContent = `${n} de ${DADOS.length} validadas`;
}

async function alterna(id, revisado, botao) {
  botao.disabled = true;
  const r = await fetch('api/revisar', {
    method: 'POST',
    body: JSON.stringify({ id, revisado }),
  });
  const res = await r.json();
  botao.disabled = false;
  if (!res.ok) return;

  const e = DADOS.find(x => x.id === id);
  e.revisado = revisado;
  botao.textContent = revisado ? 'Validada — desfazer' : 'Validar fundamentação';
  botao.className = revisado ? 'secundario' : 'primario';
  botao.closest('.revisao-item').classList.toggle('validada', revisado);
  contar();
}

iniciar();
