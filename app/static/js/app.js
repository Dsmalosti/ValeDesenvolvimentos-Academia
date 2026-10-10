/* ==========================================================================
   Vale Tec — app.js
   JavaScript puro, sem dependências. Cada comportamento é ativado por
   atributos data-* no HTML, então o Jinja (do Flask) só precisa escrever o
   atributo certo; nenhum seletor de página fica hardcoded aqui.

   Atributos suportados:
     data-open="id"           abre <dialog id="id"> (modal, sheet ou gaveta)
     data-open-aba="aba"      junto com data-open: já abre na aba (data-tabs) de id "pnl-aba"
     data-close               fecha o <dialog> mais próximo
     data-mask="cpf|telefone|dinheiro|data|cep"
     data-validate            no <form>: valida no cliente (o servidor valida de novo)
     data-opcoes              grupo .opcoes: sincroniza aria-pressed com <input type=hidden>
     data-tabs                grupo de abas (.seg__btn[aria-controls])
     data-filtro-grupo        pílulas que filtram [data-status] em [data-lista]
     data-busca               <input> que filtra [data-nome] em [data-lista]
     data-copiar="texto"      copia para a área de transferência
     data-contagem="segundos" contagem regressiva (PIX)
     data-toast="msg"         mostra um toast ao clicar (feedback de UI)
     data-passos              assistente em etapas (avaliação)
     data-popup               <dialog> que abre sozinho uma vez por sessão
     data-valor-de="id"       espelha o data-valor da <option> escolhida em outro elemento
     data-fit[="min px"]      texto numa linha só: a letra encolhe até caber (mín. 80% do tamanho do CSS); só no limite vira "…"
                              (nome, meta, valor, rótulo, botão… já recebem isso sozinhos: FIT_AUTO, mesma lista do CSS 11b)
     ?destaque=<id>           na URL: o [data-plano=id] visível rola até o centro e pisca (gráfico do faturamento -> Planos)
     data-fit-grupo           no pai de vários data-fit: todos usam o mesmo tamanho (o menor) — lista alinhada
   ========================================================================== */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduzMovimento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- ícones usados pelo JS (mesmo traço do design) ---------- */
  var SVG = function (inner) {
    return '<svg class="ico" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + inner + '</svg>';
  };
  var ICO = {
    ok: SVG('<path d="M4.5 12.5 9.5 17.5 19.5 6.5"/>'),
    err: SVG('<circle cx="12" cy="12" r="8.5"/><path d="M9 9l6 6M15 9l-6 6"/>'),
    warn: SVG('<path d="M12 3.5 22 20.5H2Z"/><path d="M12 9.5v5"/>')
  };

  /* ---------- diálogos (modal, sheet, gaveta) ---------- */
  function abrir(dlg, gatilho) {
    if (!dlg || dlg.open) return;
    dlg._gatilho = gatilho || document.activeElement;
    dlg.classList.remove('is-closing');
    dlg.showModal();
    var alvo = $('[data-autofocus]', dlg) || $('input:not([type=hidden]),select,textarea', dlg);
    if (alvo && window.matchMedia('(min-width: 992px)').matches) alvo.focus();
  }
  function fechar(dlg) {
    if (!dlg || !dlg.open || dlg.classList.contains('is-closing')) return;
    if (reduzMovimento) { dlg.close(); return; }
    dlg.classList.add('is-closing');
    var fim = function () { dlg.classList.remove('is-closing'); dlg.close(); };
    dlg.addEventListener('animationend', fim, { once: true });
    setTimeout(function () { if (dlg.open) fim(); }, 320);
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest('[data-open]');
    if (a) {
      var d = document.getElementById(a.getAttribute('data-open'));
      if (d) {
        e.preventDefault(); abrir(d, a);
        /* data-open-aba="risco": popup com abas (#pop-avisos) abrindo já na aba certa */
        var aba = a.getAttribute('data-open-aba');
        if (aba) { var tb = $('.seg__btn[aria-controls="pnl-' + aba + '"]', d); if (tb) tb.click(); }
      }
      return;
    }
    var f = e.target.closest('[data-close]');
    if (f) { e.preventDefault(); fechar(f.closest('dialog')); return; }
    /* clique no backdrop: o alvo é o próprio <dialog> */
    if (e.target.tagName === 'DIALOG' && e.target.open && !e.target.hasAttribute('data-no-backdrop-close')) fechar(e.target);
  });
  document.addEventListener('cancel', function (e) {
    if (e.target.tagName !== 'DIALOG') return;
    e.preventDefault();
    /* popup obrigatório (ex.: perfil no login): Esc só fecha depois da escolha */
    if (e.target.hasAttribute('data-obrigatorio') && !$('[aria-pressed="true"]', e.target)) return;
    fechar(e.target);
  }, true);
  document.addEventListener('close', function (e) {
    var d = e.target;
    if (d.tagName === 'DIALOG' && d._gatilho && document.contains(d._gatilho)) { try { d._gatilho.focus(); } catch (_) {} }
  }, true);

  /* ---------- toasts (aria-live) ---------- */
  function toast(msg, tipo, ms) {
    var caixa = $('#toasts');
    if (!caixa) return;
    tipo = tipo || 'ok';
    var t = document.createElement('div');
    t.className = 'toast toast--' + tipo;
    t.setAttribute('role', tipo === 'err' ? 'alert' : 'status');
    t.innerHTML = (ICO[tipo] || ICO.ok) + '<span></span>';
    t.lastChild.textContent = msg;
    caixa.appendChild(t);
    setTimeout(function () {
      t.classList.add('is-leaving');
      setTimeout(function () { t.remove(); }, 260);
    }, ms || 3800);
  }
  window.VT = window.VT || {};
  window.VT.toast = toast;
  window.VT.abrir = function (id) { abrir(document.getElementById(id)); };
  window.VT.fechar = function (id) { fechar(document.getElementById(id)); };

  /* mensagens do Flask (get_flashed_messages) chegam em <script id="flash-data" type="application/json"> */
  var flash = $('#flash-data');
  if (flash) {
    try {
      JSON.parse(flash.textContent).forEach(function (m, i) {
        var cat = m[0] === 'error' || m[0] === 'danger' ? 'err' : (m[0] === 'warning' ? 'warn' : 'ok');
        setTimeout(function () { toast(m[1], cat); }, 250 + i * 300);
      });
    } catch (_) {}
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-toast]');
    if (b) toast(b.getAttribute('data-toast'), b.getAttribute('data-toast-tipo') || 'ok');
  });

  /* ---------- máscaras e validação pt-BR ---------- */
  var so = function (v) { return (v || '').replace(/\D/g, ''); };
  var MASCARAS = {
    cpf: function (v) {
      v = so(v).slice(0, 11);
      return v.replace(/^(\d{3})(\d)/, '$1.$2').replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3').replace(/\.(\d{3})(\d)/, '.$1-$2');
    },
    telefone: function (v) {
      v = so(v).slice(0, 11);
      if (v.length <= 2) return v ? '(' + v : '';
      if (v.length <= 6) return '(' + v.slice(0, 2) + ') ' + v.slice(2);
      if (v.length <= 10) return '(' + v.slice(0, 2) + ') ' + v.slice(2, 6) + '-' + v.slice(6);
      return '(' + v.slice(0, 2) + ') ' + v.slice(2, 7) + '-' + v.slice(7);
    },
    data: function (v) {
      v = so(v).slice(0, 8);
      return v.replace(/^(\d{2})(\d)/, '$1/$2').replace(/^(\d{2})\/(\d{2})(\d)/, '$1/$2/$3');
    },
    cep: function (v) { v = so(v).slice(0, 8); return v.replace(/^(\d{5})(\d)/, '$1-$2'); },
    dinheiro: function (v) {
      v = so(v).replace(/^0+/, '');
      if (!v) return '';
      while (v.length < 3) v = '0' + v;
      var cent = v.slice(-2), int = v.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
      return int + ',' + cent;
    }
  };
  document.addEventListener('input', function (e) {
    var i = e.target;
    if (i.matches && i.matches('[data-mask]')) {
      var f = MASCARAS[i.getAttribute('data-mask')];
      if (f) i.value = f(i.value);
    }
    if (i.classList && i.classList.contains('is-invalid')) limparErro(i);
  });

  function cpfValido(c) {
    c = so(c);
    if (c.length !== 11 || /^(\d)\1+$/.test(c)) return false;
    for (var t = 9; t < 11; t++) {
      var s = 0;
      for (var k = 0; k < t; k++) s += +c[k] * (t + 1 - k);
      if (((s * 10) % 11) % 10 !== +c[t]) return false;
    }
    return true;
  }
  function dataValida(v, futuroOk) {
    var m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(v);
    if (!m) return false;
    var d = new Date(+m[3], +m[2] - 1, +m[1]);
    return d.getFullYear() === +m[3] && d.getMonth() === +m[2] - 1 && d.getDate() === +m[1] && (futuroOk || d <= new Date()) && d.getFullYear() > 1900;
  }
  function erroDe(i) {
    var v = (i.value || '').trim();
    if (i.hasAttribute('required') && !v) return i.getAttribute('data-msg-required') || 'Preencha este campo.';
    if (!v) return '';
    var m = i.getAttribute('data-mask');
    if (m === 'cpf' && !cpfValido(v)) return 'CPF inválido. Confira os 11 números.';
    if (m === 'telefone' && so(v).length < 10) return 'Telefone incompleto. Use DDD + número.';
    if (m === 'data' && !dataValida(v, i.hasAttribute('data-futuro-ok'))) return 'Data inválida. Use dia/mês/ano.';
    if (i.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) return 'E-mail inválido.';
    if (i.getAttribute('data-min') && v.length < +i.getAttribute('data-min')) return 'Mínimo de ' + i.getAttribute('data-min') + ' caracteres.';
    return '';
  }
  function marcarErro(i, msg) {
    i.classList.add('is-invalid');
    i.setAttribute('aria-invalid', 'true');
    var wrap = i.closest('.field-group') || i.parentNode;
    var alvo = $('.field-error', wrap);
    if (!alvo) {
      alvo = document.createElement('div');
      alvo.className = 'field-error';
      alvo.id = (i.id || i.name || 'campo') + '-erro';
      wrap.appendChild(alvo);
    }
    alvo.textContent = msg;
    i.setAttribute('aria-describedby', alvo.id);
  }
  function limparErro(i) {
    i.classList.remove('is-invalid');
    i.removeAttribute('aria-invalid');
    var wrap = i.closest('.field-group') || i.parentNode;
    var alvo = $('.field-error[data-js]', wrap) || $('.field-error', wrap);
    if (alvo && !alvo.hasAttribute('data-server')) alvo.remove();
  }
  document.addEventListener('focusout', function (e) {
    var i = e.target;
    if (i.matches && i.matches('form[data-validate] .input') && i.value !== '') {
      var m = erroDe(i);
      if (m) marcarErro(i, m); else limparErro(i);
    }
  });
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form.matches('form[data-validate]')) return;
    var primeiro = null;
    $$('.input', form).forEach(function (i) {
      if (i.disabled || i.closest('[hidden]')) return;
      var m = erroDe(i);
      if (m) { marcarErro(i, m); if (!primeiro) primeiro = i; } else limparErro(i);
    });
    if (primeiro) {
      e.preventDefault();
      primeiro.focus();
      toast('Revise os campos destacados.', 'err');
      return;
    }
    var envio = $('[type=submit][data-carregando]', form);
    if (envio) { envio.setAttribute('aria-disabled', 'true'); envio.classList.add('is-loading'); }
  });

  /* ---------- .opcao (escolha única) ---------- */
  document.addEventListener('click', function (e) {
    var op = e.target.closest('.opcoes[data-opcoes] .opcao');
    if (!op || op.disabled) return;
    var grupo = op.closest('.opcoes');
    $$('.opcao', grupo).forEach(function (o) { o.setAttribute('aria-pressed', o === op ? 'true' : 'false'); });
    var alvo = grupo.getAttribute('data-alvo');
    var hidden = alvo ? document.getElementById(alvo) : $('input[type=hidden]', grupo.parentNode);
    if (hidden) hidden.value = op.getAttribute('data-valor') || '';
    /* espelho: data-e-<chave> na opção -> [data-e="<chave>"] na página */
    Array.prototype.forEach.call(op.attributes, function (at) {
      if (at.name.indexOf('data-e-') !== 0) return;
      $$('[data-e="' + at.name.slice(7) + '"]').forEach(function (t) { t.textContent = at.value; });
    });
    grupo.dispatchEvent(new CustomEvent('opcao', { bubbles: true, detail: { valor: op.getAttribute('data-valor'), el: op } }));
  });

  /* ---------- abas segmentadas ---------- */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-tabs] .seg__btn[aria-controls]');
    if (!b) return;
    var grupo = b.closest('[data-tabs]');
    $$('.seg__btn', grupo).forEach(function (x) {
      var on = x === b;
      x.setAttribute('aria-selected', on ? 'true' : 'false');
      x.tabIndex = on ? 0 : -1;
      var p = document.getElementById(x.getAttribute('aria-controls'));
      if (p) p.hidden = !on;
    });
  });
  document.addEventListener('keydown', function (e) {
    var b = e.target.closest && e.target.closest('[data-tabs] .seg__btn');
    if (!b || (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft')) return;
    var todos = $$('.seg__btn', b.closest('[data-tabs]'));
    var n = todos[(todos.indexOf(b) + (e.key === 'ArrowRight' ? 1 : -1) + todos.length) % todos.length];
    n.focus(); n.click(); e.preventDefault();
  });

  /* ---------- filtro + busca em listas (tabela desktop e lista mobile juntas) ---------- */
  function aplicarFiltro(lista) {
    var status = lista._status || 'todos';
    var termo = (lista._termo || '').toLowerCase().trim();
    var termoNum = so(termo);
    var vis = 0;
    $$('[data-status]', lista).forEach(function (li) {
      var okS = status === 'todos' || li.getAttribute('data-status') === status;
      var nome = (li.getAttribute('data-nome') || '').toLowerCase();
      var cpf = so(li.getAttribute('data-cpf') || '');
      var okB = !termo || nome.indexOf(termo) > -1 || (termoNum.length > 2 && cpf.indexOf(termoNum) > -1);
      var mostra = okS && okB;
      li.hidden = !mostra;
      if (mostra) vis++;
    });
    /* cada linha existe 2x (tabela + lista mobile): conta só a visível no layout atual */
    var visiveis = $$('[data-status]:not([hidden])', lista).filter(function (x) { return x.offsetParent !== null; }).length;
    var vazio = $('[data-vazio]', lista.parentNode) || $('[data-vazio]', document);
    if (vazio) vazio.hidden = visiveis > 0;
    var cont = $$('[data-contagem-lista]');
    cont.forEach(function (c) { c.textContent = visiveis; });
  }
  function listaDe(el) { return document.getElementById(el.getAttribute('data-alvo') || 'lista-principal'); }
  document.addEventListener('click', function (e) {
    var p = e.target.closest('[data-filtro-grupo] .pill');
    if (!p) return;
    var grupo = p.closest('[data-filtro-grupo]');
    $$('.pill', grupo).forEach(function (x) { x.setAttribute('aria-pressed', x === p ? 'true' : 'false'); });
    var lista = listaDe(grupo);
    if (lista) { lista._status = p.getAttribute('data-filtro'); aplicarFiltro(lista); }
  });
  document.addEventListener('input', function (e) {
    var b = e.target.closest && e.target.closest('[data-busca]');
    if (!b) return;
    var lista = listaDe(b);
    if (lista) { lista._termo = b.value; aplicarFiltro(lista); }
  });
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-limpar-busca]');
    if (!b) return;
    var campo = $('[data-busca]');
    if (campo) { campo.value = ''; campo.dispatchEvent(new Event('input', { bubbles: true })); campo.focus(); }
  });


  /* ---------- busca remota (servidor devolve um pedaço de HTML: ?q=...&partial=1) ---------- */
  var timerRemoto;
  document.addEventListener('input', function (e) {
    var i = e.target.closest && e.target.closest('[data-remoto]');
    if (!i) return;
    var alvo = document.getElementById(i.getAttribute('data-alvo'));
    if (!alvo) return;
    clearTimeout(timerRemoto);
    var q = i.value.trim();
    if (q.length < 2) { alvo.innerHTML = '<p class="faint" style="margin:0">Digite pelo menos 2 letras para buscar.</p>'; return; }
    timerRemoto = setTimeout(function () {
      var url = i.getAttribute('data-remoto') + (i.getAttribute('data-remoto').indexOf('?') > -1 ? '&' : '?') + 'q=' + encodeURIComponent(q) + '&partial=1';
      fetch(url, { headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
        .then(function (h) { alvo.innerHTML = h; })
        .catch(function () { alvo.innerHTML = '<p class="bad" style="margin:0">Não consegui buscar agora. Tente de novo.</p>'; });
    }, 250);
  });

  /* ---------- foto: "Tirar foto" liga a câmera (capture); "galeria" desliga ---------- */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-foto-abrir]');
    if (!b) return;
    var f = b.getAttribute('data-alvo-foto') ? $(b.getAttribute('data-alvo-foto')) : document.getElementById('f-foto');
    if (b.getAttribute('data-foto-abrir') === 'camera') f.setAttribute('capture', 'user'); else f.removeAttribute('capture');
    f.click();
  });

  /* ---------- pré-visualização da foto escolhida ---------- */
  document.addEventListener('change', function (e) {
    var f = e.target.closest && e.target.closest('input[data-foto]');
    if (!f || !f.files || !f.files[0]) return;
    var alvo = document.querySelector('[data-foto-previa]');
    if (!alvo) return;
    var url = URL.createObjectURL(f.files[0]);
    alvo.innerHTML = '<img src="' + url + '" alt="Foto escolhida" style="width:100%;height:100%;object-fit:cover;border-radius:inherit">';
  });

  /* ---------- atalho que leva o foco a um campo: data-foco="#id" ---------- */
  document.addEventListener('click', function (e) {
    var a = e.target.closest('[data-foco]');
    if (!a) return;
    var alvo = $(a.getAttribute('data-foco'));
    if (alvo && alvo.offsetParent !== null) { e.preventDefault(); alvo.scrollIntoView({ block: 'center', behavior: reduzMovimento ? 'auto' : 'smooth' }); alvo.focus({ preventScroll: true }); }
  });

  /* ---------- copiar ---------- */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-copiar]');
    if (!b) return;
    var txt = b.getAttribute('data-copiar');
    var ok = function () { toast(b.getAttribute('data-copiar-msg') || 'Copiado.', 'ok'); };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(txt).then(ok, function () { toast('Não consegui copiar. Selecione e copie manualmente.', 'err'); });
    else {
      var t = document.createElement('textarea'); t.value = txt; t.style.position = 'fixed'; t.style.opacity = '0';
      document.body.appendChild(t); t.select();
      try { document.execCommand('copy'); ok(); } catch (_) { toast('Não consegui copiar.', 'err'); }
      t.remove();
    }
  });

  /* ---------- contagem regressiva (validade do PIX) ---------- */
  $$('[data-contagem]').forEach(function (el) {
    var fim = Date.now() + (+el.getAttribute('data-contagem')) * 1000;
    var fmt = function (s) { return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); };
    var t = setInterval(function () {
      var s = Math.max(0, Math.round((fim - Date.now()) / 1000));
      el.textContent = fmt(s);
      if (s === 0) {
        clearInterval(t);
        el.dispatchEvent(new CustomEvent('expirou', { bubbles: true }));
        var painel = document.querySelector('[data-pix-expirado]');
        if (painel) painel.hidden = false;
      }
    }, 1000);
    el.textContent = fmt(+el.getAttribute('data-contagem'));
  });

  /* ---------- espelhar valor do plano escolhido ---------- */
  $$('select[data-valor-de]').forEach(function (sel) {
    var alvos = $$('[data-valor-alvo="' + sel.id + '"]');
    var brl = function (n) { return 'R$ ' + Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };
    var upd = function () {
      var o = sel.options[sel.selectedIndex];
      alvos.forEach(function (a) {
        var v = o && o.getAttribute('data-valor');
        var d = o && o.getAttribute('data-dias');
        a.textContent = v ? (a.hasAttribute('data-com-dias') && d ? brl(v) + ' · ' + d + ' dias' : brl(v)) : '—';
      });
    };
    sel.addEventListener('change', upd); upd();
  });

  /* ---------- assistente em etapas (registrar avaliação) ---------- */
  $$('[data-passos]').forEach(function (raiz) {
    var passos = $$('[data-passo]', raiz);
    var atual = 0;
    var barra = $$('[data-passo-ind]', raiz);
    var titulo = $('[data-passo-titulo]', raiz);
    function ir(n) {
      atual = Math.max(0, Math.min(passos.length - 1, n));
      passos.forEach(function (p, i) { p.hidden = i !== atual; });
      barra.forEach(function (b, i) { b.classList.toggle('on', i <= atual); b.setAttribute('aria-current', i === atual ? 'step' : 'false'); });
      if (titulo) titulo.textContent = passos[atual].getAttribute('data-passo-nome') || '';
      $$('[data-ant]', raiz).forEach(function (b) { b.hidden = atual === 0; });
      $$('[data-prox]', raiz).forEach(function (b) { b.hidden = atual === passos.length - 1; });
      $$('[type=submit]', raiz).forEach(function (b) { b.hidden = atual !== passos.length - 1; });
      raiz.scrollIntoView({ block: 'start', behavior: reduzMovimento ? 'auto' : 'smooth' });
      raiz.dispatchEvent(new CustomEvent('passo', { detail: atual }));
    }
    raiz.addEventListener('click', function (e) {
      if (e.target.closest('[data-prox]')) {
        var invalido = null;
        $$('.input', passos[atual]).forEach(function (i) { var m = erroDe(i); if (m) { marcarErro(i, m); invalido = invalido || i; } else limparErro(i); });
        if (invalido) { invalido.focus(); return; }
        ir(atual + 1);
      }
      if (e.target.closest('[data-ant]')) ir(atual - 1);
    });
    ir(0);
  });

  /* ---------- pré-visualização de IMC no assistente (o servidor recalcula; isto é só espelho) ---------- */
  document.addEventListener('input', function (e) {
    if (!e.target.closest || !e.target.closest('[data-passos]')) return;
    var p = $('[name=peso_kg]'), a = $('[name=altura_cm]'), out = $('[data-imc-previa]');
    if (!p || !a || !out) return;
    var kg = parseFloat((p.value || '').replace(',', '.')), m = parseFloat((a.value || '').replace(',', '.')) / 100;
    var imc = kg > 0 && m > 0 ? kg / (m * m) : 0;
    out.textContent = imc ? imc.toFixed(1).replace('.', ',') : '—';
    var chip = $('[data-imc-chip]');
    if (chip) {
      var faixa = !imc ? ['', ''] : imc < 18.5 ? ['Abaixo do peso', 'yellow'] : imc < 25 ? ['Peso normal', 'green'] : imc < 30 ? ['Sobrepeso', 'yellow'] : ['Acima do ideal', 'red'];
      chip.textContent = faixa[0]; chip.className = 'chip' + (faixa[1] ? ' chip--' + faixa[1] : ''); chip.hidden = !imc;
    }
    var c = $('[name=cintura_cm]'), q = $('[name=quadril_cm]'), r = $('[data-rcq-previa]');
    if (c && q && r) {
      var cc = parseFloat((c.value || '').replace(',', '.')), qq = parseFloat((q.value || '').replace(',', '.'));
      r.textContent = cc > 0 && qq > 0 ? (cc / qq).toFixed(2).replace('.', ',') : '—';
    }
  });

  /* ---------- pop-ups automáticos: um por vez, cada um uma vez por sessão ---------- */
  var filaPopups = $$('dialog[data-popup]').filter(function (d) {
    try { return !sessionStorage.getItem('vt-popup-' + d.id); } catch (_) { return true; }
  });
  function proximoPopup(atraso) {
    var d = filaPopups.shift();
    if (!d) return;
    setTimeout(function () {
      if (document.querySelector('dialog[open]')) { filaPopups.unshift(d); return; }
      abrir(d);
      try { sessionStorage.setItem('vt-popup-' + d.id, '1'); } catch (_) {}
      d.addEventListener('close', function () { proximoPopup(500); }, { once: true });
    }, atraso);
  }
  proximoPopup(900);

  /* ---------- blocos que só existem para certa forma de pagamento: data-so-forma="pix debito" ---------- */
  function aplicarForma(v) {
    $$('[data-so-forma]').forEach(function (el) {
      el.hidden = (' ' + el.getAttribute('data-so-forma') + ' ').indexOf(' ' + v + ' ') === -1;
    });
  }
  var grupoForma = $('.opcoes[data-controla-forma]');
  if (grupoForma) {
    var h0 = document.getElementById(grupoForma.getAttribute('data-alvo'));
    if (h0) aplicarForma(h0.value);
    document.addEventListener('opcao', function (e) { if (e.target === grupoForma) aplicarForma(e.detail.valor); });
  }

  /* ---------- troco (dinheiro): [data-troco-de] lê o total, escreve em [data-troco] ---------- */
  document.addEventListener('input', function (e) {
    var i = e.target.closest && e.target.closest('[data-recebido]');
    if (!i) return;
    var num = function (t) { return parseFloat(String(t).replace(/\./g, '').replace(',', '.')) || 0; };
    var total = num(i.getAttribute('data-recebido')), rec = num(i.value);
    $$('[data-troco]').forEach(function (t) {
      var d = rec - total;
      t.textContent = d > 0 ? 'Troco: R$ ' + d.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : (d < 0 && rec ? 'Faltam R$ ' + (-d).toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '');
    });
  });

  /* ---------- acompanha o status de uma cobrança (PIX): recarrega quando o banco confirmar ---------- */
  var poll = $('[data-poll]');
  if (poll) {
    var urlPoll = poll.getAttribute('data-poll');
    var ciclo = setInterval(function () {
      if (document.hidden) return;
      fetch(urlPoll, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (j) { if (j.estado === 'confirmado') { clearInterval(ciclo); location.reload(); } })
        .catch(function () {});
    }, 4000);
  }

  /* ---------- diálogo que já nasce aberto (ex.: erro de validação do servidor no modal) ---------- */
  $$('dialog[data-abrir]').forEach(function (d) { abrir(d); });

  /* ---------- mostrar/ocultar senha ---------- */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-toggle-senha]');
    if (!b) return;
    var i = document.getElementById(b.getAttribute('data-toggle-senha'));
    if (!i) return;
    var vendo = i.type === 'text';
    i.type = vendo ? 'password' : 'text';
    b.setAttribute('aria-label', vendo ? 'Mostrar senha' : 'Ocultar senha');
    b.setAttribute('aria-pressed', vendo ? 'false' : 'true');
  });

  /* ---------- interruptor que mostra/oculta um bloco ---------- */
  document.addEventListener('change', function (e) {
    var s = e.target.closest && e.target.closest('input[data-mostra]');
    if (!s) return;
    var alvo = document.getElementById(s.getAttribute('data-mostra'));
    if (alvo) alvo.hidden = !s.checked;
  });

  /* ---------- seleção por lote (checkbox mestre) ---------- */
  document.addEventListener('change', function (e) {
    var m = e.target.closest && e.target.closest('[data-marcar-todos]');
    if (m) $$(m.getAttribute('data-marcar-todos')).forEach(function (c) { c.checked = m.checked; c.dispatchEvent(new Event('change', { bubbles: true })); });
    if (e.target.matches && e.target.matches('[data-item-lote]')) {
      var n = $$('[data-item-lote]:checked').length;
      $$('[data-lote-qtd]').forEach(function (x) { x.textContent = n; });
      $$('[data-lote-acao]').forEach(function (x) { x.disabled = n === 0; x.setAttribute('aria-disabled', n === 0 ? 'true' : 'false'); });
    }
  });

  /* ---------- switch que salva sozinho (form[data-auto-submit]) ---------- */
  document.addEventListener('change', function (e) {
    var f = e.target.closest && e.target.closest('form[data-auto-submit]');
    if (f && e.target.matches('input[type=checkbox]')) {
      var h = f.querySelector('input[name=ligado]'); if (h) h.value = e.target.checked ? '1' : '0';
      f.requestSubmit ? f.requestSubmit() : f.submit();
    }
  });

  /* ---------- imprimir a página (ficha de treino) ---------- */
  document.addEventListener('click', function (e) { if (e.target.closest('[data-imprimir]')) window.print(); });

  /* ---------- botão "voltar" das páginas de erro ---------- */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-voltar]'); if (!b) return;
    /* há "página anterior" do próprio sistema? então volta nela; senão segue o href (Painel) */
    var veioDoSistema = document.referrer && document.referrer.indexOf(location.origin) === 0 && history.length > 1;
    if (veioDoSistema) { e.preventDefault(); history.back(); }
    else if (b.tagName === 'BUTTON') { location.href = b.getAttribute('data-voltar') || '/'; }
  });

  /* ---------- filtros com rolagem lateral (.pills / .seg) ----------
     Toque já rola sozinho; aqui entram mouse (arrastar + roda), o item ativo
     centralizado e a "sombra" nas bordas indicando que há mais opções. */
  (function () {
    function marcar(el) {
      var max = el.scrollWidth - el.clientWidth;
      el.classList.toggle('is-scroll-l', el.scrollLeft > 4);
      el.classList.toggle('is-scroll-r', max > 4 && el.scrollLeft < max - 4);
    }
    function iniciar(el) {
      if (el.__rolagem) return; el.__rolagem = true;
      var ativo = el.querySelector('[aria-current="true"],[aria-selected="true"]');
      if (ativo && el.scrollWidth > el.clientWidth) {
        el.scrollLeft = ativo.offsetLeft - (el.clientWidth - ativo.offsetWidth) / 2;
      }
      marcar(el);
      el.addEventListener('scroll', function () { marcar(el); }, { passive: true });
      window.addEventListener('resize', function () { marcar(el); });
      el.addEventListener('wheel', function (e) {
        if (el.scrollWidth <= el.clientWidth || Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
        el.scrollLeft += e.deltaY; e.preventDefault();
      }, { passive: false });
      var x0 = 0, s0 = 0, arrastando = false, moveu = false;
      el.addEventListener('pointerdown', function (e) {
        if (e.pointerType !== 'mouse' || e.button !== 0 || el.scrollWidth <= el.clientWidth) return;
        arrastando = true; moveu = false; x0 = e.clientX; s0 = el.scrollLeft;
      });
      window.addEventListener('pointermove', function (e) {
        if (!arrastando) return;
        var dx = e.clientX - x0;
        if (Math.abs(dx) > 5) { moveu = true; el.classList.add('is-arrastando'); }
        if (moveu) el.scrollLeft = s0 - dx;
      });
      window.addEventListener('pointerup', function () {
        if (!arrastando) return; arrastando = false; el.classList.remove('is-arrastando');
      });
      el.addEventListener('click', function (e) { if (moveu) { e.preventDefault(); e.stopPropagation(); moveu = false; } }, true);
      el.addEventListener('dragstart', function (e) { e.preventDefault(); });
    }
    function todos() { $$('.pills, .seg').forEach(iniciar); }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', todos); else todos();
    window.addEventListener('load', todos);
  })();

  /* ---------- data-fit: texto numa linha só, a letra encolhe até caber ----------
     Por que JS e não só CSS? O CSS (cqi/clamp) sabe a largura da caixa, mas não sabe o tamanho do TEXTO —
     e aqui o texto é dado do cliente ("Plano Família Anual Promocional"). Então medimos de verdade:
     se o conteúdo (scrollWidth) passa da caixa (clientWidth), reduzimos a fonte na proporção exata.
     Requisitos no CSS do elemento: white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0.
     Filhos com tamanho em "em" encolhem junto (ex.: nome + meta do "De onde vem o faturamento"). */
  (function () {
    // componentes de DADO que já nascem "numa linha só" (mesma lista do CSS, seção 11b) — não precisa marcar no HTML
    var FIT_AUTO = '.mrow__title,.mrow__sub,.av-quem b,.av-quem .faint,.ag-quem b,.ag-quem small,.set-row__t,.alert-card b,.alert-card__sub,' +
      '.kpi__lbl,.kpi__val,.stat__val,.stat__lbl,.rkpi__val,.rkpi__lbl,.rkpi__sub,.mini__lbl,.mini__val,.plano__valor,' +
      '.ctitle,.page-title,.btn,.opcao,.opcao-sub,.qa,.tab-treino,.pop-item b,.linha1';
    var SEL = '[data-fit],' + FIT_AUTO;
    var els = $$(SEL); if (!els.length) return;
    var CURTO = 12;   // abaixo disso, se existir versão curta (.txt-curto: "30d" no lugar de "30 dias"), troca antes de encolher mais
    function medir(el, w) {
      el.style.fontSize = '';
      var base = parseFloat(getComputedStyle(el).fontSize), s = base;
      if (el.scrollWidth > w) {                          // não cabe no tamanho do CSS -> reduz na proporção
        var min = parseFloat(el.getAttribute('data-fit')) || Math.max(10, Math.round(base * 0.8 * 4) / 4);   // até 80% do design
        s = Math.max(min, Math.floor(base * w / el.scrollWidth * 4) / 4);
        el.style.fontSize = s + 'px';
        while (el.scrollWidth > el.clientWidth && s > min) { s = Math.max(min, s - 0.25); el.style.fontSize = s + 'px'; }
        if (s > min) { s = Math.max(min, s - 0.25); el.style.fontSize = s + 'px'; }   // folga de subpixel (scrollWidth é arredondado)
      }
      el._fitS = s; el._fitB = base; return s;
    }
    function ajustar(el, forcar) {
      var w = el.clientWidth; if (!w) return false;      // dentro de <dialog> fechado: mede quando abrir
      if (!forcar && el._fitW === w) return false;       // só recalcula se a LARGURA mudou (evita loop do observer)
      el._fitW = w;
      el.classList.remove('fit-curto');
      if (medir(el, w) < CURTO && el.querySelector('.txt-curto')) { el.classList.add('fit-curto'); medir(el, w); }
      return true;
    }
    // data-fit-grupo no pai: as linhas de uma mesma lista usam o MESMO tamanho (o menor) e a mesma versão (longa/curta),
    // senão a lista fica "dentada"
    function igualar(grupos) {
      grupos.forEach(function (g) {
        var itens = $$(SEL, g).filter(function (el) { return el.clientWidth; });
        if (itens.some(function (el) { return el.classList.contains('fit-curto'); })) {
          itens.forEach(function (el) { if (!el.classList.contains('fit-curto') && el.querySelector('.txt-curto')) { el.classList.add('fit-curto'); medir(el, el.clientWidth); } });
        }
        var menor = Math.min.apply(null, itens.map(function (el) { return el._fitS || Infinity; }));
        if (menor === Infinity) return;
        itens.forEach(function (el) { el.style.fontSize = menor < (el._fitB || menor) ? menor + 'px' : ''; });
      });
    }
    function rodar(lista, forcar) {
      var grupos = [];
      lista.forEach(function (el) {
        if (ajustar(el, forcar)) { var g = el.closest('[data-fit-grupo]'); if (g && grupos.indexOf(g) < 0) grupos.push(g); }
      });
      // uma linha mudou -> o grupo inteiro é refeito do zero (ela pode ter "puxado" as outras para a versão curta)
      grupos.forEach(function (g) { $$(SEL, g).forEach(function (el) { if (lista.indexOf(el) < 0) ajustar(el, true); }); });
      igualar(grupos);
    }
    if ('ResizeObserver' in window) {
      var ro = new ResizeObserver(function (entradas) { rodar(entradas.map(function (r) { return r.target; })); });
      els.forEach(function (el) { ro.observe(el); });
    } else {
      rodar(els, true);
      window.addEventListener('resize', function () { rodar(els, true); });
    }
    // fonte web carregou depois -> a largura do texto muda; força nova medida
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { rodar(els, true); });
    window.VT.refit = function () { rodar(els, true); };   /* texto mudou sem a largura mudar (ex.: número contando) */
  })();

  /* ---------- ?destaque=<id>: veio do gráfico "De onde vem o faturamento" -> mostra QUAL plano ----------
     Cartão de desktop e de celular existem os dois no HTML; pega o que está visível (offsetParent). */
  (function () {
    var id = new URLSearchParams(location.search).get('destaque'); if (!id) return;
    var alvo = $$('[data-plano="' + CSS.escape(id) + '"]').filter(function (el) { return el.offsetParent !== null; })[0];
    if (!alvo) return;
    var suave = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    requestAnimationFrame(function () {
      alvo.scrollIntoView({ block: 'center', behavior: suave ? 'smooth' : 'auto' });
      alvo.classList.add('is-destaque');
      setTimeout(function () { alvo.classList.remove('is-destaque'); }, 2400);
    });
  })();

  /* ---------- popup de perfil do login (#dlg-perfil) ---------- */
  (function () {
    var dlg = document.getElementById('dlg-perfil'); if (!dlg) return;
    var chip = $('[data-perfil-chip]'), nome = $('[data-perfil-nome]');
    if (dlg.hasAttribute('data-abrir-auto')) abrir(dlg);
    dlg.addEventListener('click', function (e) {
      var op = e.target.closest('.opcao'); if (!op) return;
      if (nome) nome.textContent = $('.grow', op).firstChild.textContent.trim();
      if (chip) chip.hidden = false;
      fechar(dlg);
      var id = $('input[name=identificador]'); if (id && window.matchMedia('(min-width: 992px)').matches) id.focus();
    });
  })();
  /* ==========================================================================
     "Cara de app" (rodada 8 — pedido: sistema mais tecnológico, SEM mudar layout)
     Peso Emil Kowalski (painel usado o dia todo): o que se repete muito não anima; tudo curto; reduced-motion respeitado.
     ========================================================================== */
  var calmo = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* 1) Abrir telas na hora: quando o dedo ENCOSTA no link (ou o mouse para em cima ~200 ms), o navegador já busca a
        próxima página (Speculation Rules, "prefetch"). Ao soltar, ela abre quase instantânea. Só GET do próprio sistema;
        nada de sair/exportar/dev. Navegador sem suporte simplesmente ignora. */
  (function () {
    if (!HTMLScriptElement.supports || !HTMLScriptElement.supports('speculationrules')) return;
    var regra = document.createElement('script');
    regra.type = 'speculationrules';
    regra.textContent = JSON.stringify({ prefetch: [{
      source: 'document', eagerness: 'moderate',
      where: { and: [
        { href_matches: '/*' },
        { not: { href_matches: '/_dev/*' } },
        { not: { href_matches: '/*exportar*' } },
        { not: { href_matches: '/login' } },
        { not: { selector_matches: '[download], [data-sem-prefetch], [target=_blank]' } }
      ] }
    }] });
    document.head.appendChild(regra);
  })();

  /* 2) Números dos cards "contando" — só na PRIMEIRA vez que a tela abre na sessão (tela vista 50x/dia não anima).
        Mantém o formato (R$, ponto de milhar, vírgula); fonte tabular, então o card não "treme". */
  (function () {
    var nums = $$('.kpi__val, .mini__val, .stat__val, .rkpi__val'); if (!nums.length || calmo) return;
    var chave = 'vt-contou:' + location.pathname;
    try { if (sessionStorage.getItem(chave)) return; sessionStorage.setItem(chave, '1'); } catch (_) { return; }
    nums.forEach(function (el) {
      if (el.children.length) return;                                   /* só texto puro */
      var txt = el.textContent.trim(), m = txt.match(/^([^\d-]*)(-?[\d.]+(?:,\d+)?)(.*)$/);
      if (!m) return;
      var casas = (m[2].split(',')[1] || '').length;
      var alvo = parseFloat(m[2].replace(/\./g, '').replace(',', '.'));
      if (!isFinite(alvo) || Math.abs(alvo) < 2) return;                 /* "1" contando não acrescenta nada */
      var fmt = function (v) { return m[1] + v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }) + m[3]; };
      var t0 = null, dur = 700;
      el.textContent = fmt(0);
      requestAnimationFrame(function passo(t) {
        if (t0 === null) t0 = t;
        var k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);   /* ease-out cúbico: rápido no começo, assenta no fim */
        el.textContent = k < 1 ? fmt(casas ? alvo * e : Math.round(alvo * e)) : txt;
        if (k < 1) requestAnimationFrame(passo); else if (window.VT.refit) window.VT.refit();
      });
    });
  })();

  /* 3) Sem internet: avisa na hora (e avisa quando voltar) em vez de deixar o usuário tocar e "nada acontecer" */
  window.addEventListener('offline', function () { toast('Sem internet. O que já está na tela continua aqui; salvar volta quando a conexão voltar.', 'warn', 6000); });
  window.addEventListener('online', function () { toast('Conexão de volta.', 'ok', 2200); });

  /* 4) Puxar pra atualizar — só no app instalado (tela cheia), onde o navegador não oferece isso sozinho.
        No navegador comum o Chrome/Safari já têm o deles: duplicar brigaria com a rolagem. */
  (function () {
    var instalado = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    if (!instalado || !('ontouchstart' in window) || !document.querySelector('.m-body')) return;
    var ind = document.createElement('div');
    ind.className = 'ptr'; ind.setAttribute('aria-hidden', 'true');
    ind.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v4.5h-4.5"/></svg>';
    document.body.appendChild(ind);
    var y0 = null, dy = 0, LIMIAR = 72, armou = false;
    document.addEventListener('touchstart', function (e) {
      if (window.scrollY > 0 || e.touches.length > 1 || e.target.closest('dialog, input, textarea, select, .chart, [data-no-swipe]')) { y0 = null; return; }
      y0 = e.touches[0].clientY; dy = 0; armou = false;
    }, { passive: true });
    document.addEventListener('touchmove', function (e) {
      if (y0 === null) return;
      dy = Math.max(0, e.touches[0].clientY - y0);
      if (!dy) return;
      var d = Math.min(110, dy * 0.5);                                  /* resistência: o indicador anda metade do dedo */
      ind.style.transform = 'translate(-50%,' + d + 'px) rotate(' + (dy * 2) + 'deg)';
      ind.style.opacity = Math.min(1, dy / LIMIAR);
      var passou = dy * 0.5 >= LIMIAR * 0.5 && dy >= LIMIAR;
      if (passou && !armou && navigator.vibrate) { try { navigator.vibrate(6); } catch (_) {} }
      armou = passou; ind.classList.toggle('is-pronto', armou);
    }, { passive: true });
    document.addEventListener('touchend', function () {
      if (y0 === null) return; y0 = null;
      if (armou) { ind.classList.add('is-girando'); location.reload(); return; }
      ind.style.transform = ''; ind.style.opacity = 0; ind.classList.remove('is-pronto');
    });
  })();

  /* voltar pelo botão do navegador traz a página "congelada" (bfcache): o botão não pode ficar girando pra sempre */
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) $$('.btn.is-loading').forEach(function (b) { b.classList.remove('is-loading'); b.removeAttribute('aria-disabled'); });
  });

  /* central de mensagens: tocou em "Enviar no WhatsApp" -> o link abre o WhatsApp (nova aba/app) e a linha vira "Enviada".
     O registro vai pro servidor em segundo plano (não segura a abertura do WhatsApp). */
  document.addEventListener('click', function (e) {
    var a = e.target.closest('[data-msg-enviar]'); if (!a) return;
    var li = a.closest('.msg-item');
    var csrf = ($('meta[name="csrf-token"]') || {}).content || '';
    try {
      fetch('/mensagens/enviada', { method: 'POST', credentials: 'same-origin', keepalive: true,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf }, body: JSON.stringify({ id: a.getAttribute('data-msg-enviar') }) });
    } catch (_) {}
    if (li) {
      li.classList.add('is-enviada');
      var f = $('[data-msg-feito]', li); if (f) f.hidden = false;
      var r = $('[data-msg-rotulo]', a); if (r) r.textContent = 'Enviar de novo';
    }
    if (navigator.vibrate) { try { navigator.vibrate(8); } catch (_) {} }
  });

  /* força da senha (criar conta / aceitar convite): barra + frase que ajuda, não regra que pune.
     Conta tamanho e variedade; o servidor só exige 8+ caracteres (a barra é conselho, não trava). */
  $$('[data-forca]').forEach(function (inp) {
    var g = inp.closest('.field-group'), barra = $('[data-forca-barra]', g), txt = $('[data-forca-txt]', g);
    var base = txt ? txt.textContent : '';
    inp.addEventListener('input', function () {
      var v = inp.value, n = 0;
      if (v.length >= 8) n++; if (v.length >= 12) n++;
      if (/[a-z]/.test(v) && /[A-Z]/.test(v)) n++; if (/\d/.test(v)) n++; if (/[^A-Za-z0-9]/.test(v) || / /.test(v)) n++;
      if (/^(.)\1+$/.test(v) || /^(12345678|senha123|password|abcdefgh)/i.test(v)) n = 0;
      var nivel = !v ? 0 : v.length < 8 ? 1 : n <= 2 ? 2 : n <= 3 ? 3 : 4;
      if (barra) { barra.style.transform = 'scaleX(' + (nivel / 4) + ')'; barra.setAttribute('data-nivel', nivel); }
      if (txt) txt.textContent = ['', 'Faltam ' + (8 - v.length) + ' caractere' + (8 - v.length === 1 ? '' : 's') + '.', 'Fraca: junte mais palavras ou números.', 'Boa.', 'Forte.'][nivel] || base;
    });
  });

  /* Aparência (Configurações > Seu acesso): Auto / Claro / Escuro. Quem guarda e aplica é o tema.js (no <head>). */
  $$('[data-tema-escolha]').forEach(function (grupo) {
    var marcar = function () {
      var atual = window.VTtema ? window.VTtema.preferencia() : 'auto';
      $$('[data-tema-opcao]', grupo).forEach(function (b) { b.setAttribute('aria-checked', b.getAttribute('data-tema-opcao') === atual ? 'true' : 'false'); });
    };
    marcar();
    grupo.addEventListener('click', function (e) {
      var b = e.target.closest('[data-tema-opcao]'); if (!b || !window.VTtema) return;
      window.VTtema.definir(b.getAttribute('data-tema-opcao'));
      $$('[data-tema-escolha]').forEach(function (g) { if (g._marcar) g._marcar(); });
      if (navigator.vibrate) { try { navigator.vibrate(6); } catch (_) {} }
    });
    /* setas do teclado entre as opções (padrão de radiogroup) */
    grupo.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      var bs = $$('[data-tema-opcao]', grupo), i = bs.indexOf(document.activeElement);
      if (i < 0) return;
      var n = bs[(i + (e.key === 'ArrowRight' ? 1 : -1) + bs.length) % bs.length]; n.focus(); n.click(); e.preventDefault();
    });
    grupo._marcar = marcar;
  });

  /* 5) Toque em botão/switch: vibração curtinha no Android ao LIGAR/DESLIGAR (confirmação física, como app nativo) */
  document.addEventListener('change', function (e) {
    if (e.target.matches('.switch input') && navigator.vibrate) { try { navigator.vibrate(8); } catch (_) {} }
  });
})();
