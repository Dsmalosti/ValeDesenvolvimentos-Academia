/* ==========================================================================
   Vale Tec — interacoes.js
   Camada de "sensação de app" (gestos, transições e microfeedback), separada
   do app.js de propósito: o app.js liga comportamento de NEGÓCIO (abrir popup,
   validar form); este arquivo só deixa a navegação com cara de rede social.
   Se este arquivo falhar ou o navegador não suportar algo, o sistema funciona
   igual — tudo aqui é melhoria progressiva.

   O que tem aqui (cada bloco é independente):
     1. Transição entre páginas (View Transitions entre documentos) com direção:
        avançar entra pela direita, voltar entra pela esquerda, troca de aba
        segue a posição da aba. CSS em app.css > "9. interações".
     2. Barra de progresso no topo enquanto a próxima página carrega.
     3. Gesto de deslizar (celular): → volta nas telas com botão voltar;
        ← / → troca de aba nas telas da barra inferior.
     4. Arrastar pra baixo fecha o popup (bottom sheet) e arrastar pra
        esquerda fecha a gaveta — com "momentum": um peteleco rápido fecha
        mesmo com pouco deslocamento.
     5. Deslizar o aviso (toast) pro lado dispensa.
     6. Linhas clicáveis: <tr data-href="/alunos/1"> abre o perfil.
     7. Tocar na aba que já está aberta volta ao topo (padrão de app).
     8. Vibração curta (Android) quando um gesto "pega".

   Regras de movimento (skills design-motion + emil-design-eng):
     - só transform/opacity (roda na GPU, não trava a rolagem);
     - saída mais curta que entrada; curva --ease-out do design system;
     - prefers-reduced-motion: sem deslocamentos, só troca direta;
     - durante o arraste o elemento segue o dedo 1:1 (sem transição) e só
       anima ao soltar.
   ========================================================================== */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduz = window.matchMedia('(prefers-reduced-motion: reduce)');
  var celular = window.matchMedia('(max-width: 991.98px)');
  var standalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  /* "Peteleco" (momentum): soltar rápido conta mesmo com pouco deslocamento — é o que faz o gesto
     parecer nativo. 0,4 px/ms é o valor usado em drawers de referência (Vaul): arrasto lento e
     deliberado não dispara; só o movimento rápido de jogar pra fora. */
  var VEL_PETELECO = 0.4;

  /* velocidade (px/ms) no fim do gesto, pelas últimas amostras. Se o dedo parou antes de soltar
     (> 80 ms sem mexer), a velocidade é zero: segurar parado e soltar não é peteleco. */
  function velocidade(amostras, campo, tFim) {
    var a = amostras[0], b = amostras[amostras.length - 1];
    if (!a || !b || b.t <= a.t || tFim - b.t > 80) return 0;
    return (b[campo] - a[campo]) / (b.t - a.t);
  }

  function vibrar(ms) {
    if (!navigator.vibrate || reduz.matches) return;
    try { navigator.vibrate(ms || 8); } catch (_) {}
  }
  function guardar(chave, valor) { try { sessionStorage.setItem(chave, valor); } catch (_) {} }
  function ler(chave) { try { var v = sessionStorage.getItem(chave); sessionStorage.removeItem(chave); return v; } catch (_) { return null; } }

  /* elemento que rola na horizontal sozinho (filtros, tabelas, gráfico)? então o gesto é dele, não da página */
  function rolaNaHorizontal(el) {
    for (; el && el !== document.body; el = el.parentElement) {
      if (el.matches('input, textarea, select, [contenteditable], dialog, .chart, .stackbar, [data-no-swipe]')) return true;
      if (el.scrollWidth > el.clientWidth + 2) {
        var ov = getComputedStyle(el).overflowX;
        if (ov === 'auto' || ov === 'scroll') return true;
      }
    }
    return false;
  }

  /* abas da barra inferior: posição da aba atual (−1 = página fora das abas) */
  function abas() { return $$('.tabbar .tabbar__item'); }
  function abaAtual() {
    var lista = abas();
    for (var i = 0; i < lista.length; i++) if (lista[i].getAttribute('aria-current') === 'page') return i;
    return -1;
  }

  /* ======================================================================
     1. Transição entre páginas com direção
     Quem suporta (Chrome/Edge 126+, Safari 18.2+) anima; quem não suporta
     navega normal. A direção vai como "tipo" da transição e o CSS escolhe a
     animação: html:active-view-transition-type(back) ...
     ====================================================================== */
  /* Este arquivo é carregado no <head> (sem defer) só por causa deste bloco:
     o evento pagereveal dispara no 1º quadro da página nova e o ouvinte
     precisa já existir. Por isso a direção é decidida na página ANTIGA
     (clique/gesto grava 'vt-dir') e a nova só lê. */
  window.addEventListener('pagereveal', function (e) {
    if (!e.viewTransition) return;
    var ativ = window.navigation && navigation.activation;
    if (ativ && ativ.navigationType === 'reload') { ler('vt-dir'); e.viewTransition.skipTransition(); return; }
    var tipo = ler('vt-dir');
    if (!tipo && ativ && ativ.navigationType === 'traverse' && ativ.from && ativ.entry) tipo = ativ.entry.index < ativ.from.index ? 'back' : 'forward';
    try { e.viewTransition.types.add(celular.matches ? (tipo || 'forward') : 'fade'); } catch (_) {}
  });
  /* "voltar" do cabeçalho (history.back) e troca de aba pela barra: grava a direção antes de sair */
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-voltar]')) { guardar('vt-dir', 'back'); return; }
    var item = e.target.closest('.tabbar__item');
    if (item) {
      var i = abas().indexOf(item), atual = abaAtual();
      if (i >= 0 && atual >= 0 && i !== atual) guardar('vt-dir', i > atual ? 'forward' : 'back');
    }
  }, true);

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciarResto); else iniciarResto();
  function iniciarResto() {

    /* ======================================================================
       2. Barra de progresso no topo
       Só aparece se a próxima página demorar mais que 120 ms (rede boa = nada
       pisca). Volta a zero quando a página é restaurada do cache (voltar).
       ====================================================================== */
    var barra = document.createElement('div');
    barra.className = 'nav-progress';
    barra.setAttribute('aria-hidden', 'true');
    document.body.appendChild(barra);
    var timerBarra = 0;
    function iniciarBarra() {
      clearTimeout(timerBarra);
      timerBarra = setTimeout(function () { barra.classList.add('is-on'); }, 120);
    }
    function pararBarra() { clearTimeout(timerBarra); barra.classList.remove('is-on'); }
    document.addEventListener('click', function (e) {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      var a = e.target.closest('a[href]');
      if (!a || a.target === '_blank' || a.hasAttribute('download') || a.hasAttribute('data-open') || a.hasAttribute('data-voltar')) return;
      var url = new URL(a.href, location.href);
      if (url.origin !== location.origin || (url.pathname === location.pathname && url.search === location.search && url.hash)) return;
      iniciarBarra();
    });
    document.addEventListener('submit', function (e) {
      if (!e.defaultPrevented && e.target.method !== 'dialog') iniciarBarra();
    });
    window.addEventListener('pageshow', function () { pararBarra(); soltarPagina(true); });

    /* ======================================================================
       3. Deslizar entre páginas (celular, toque)
       → nas telas com "voltar" no cabeçalho: volta.
       ← / → nas telas da barra inferior: aba seguinte / anterior.
       Trava de direção: só vira gesto se o dedo andou mais na horizontal que
       na vertical (senão é rolagem). No navegador, a borda da tela fica com o
       gesto nativo de voltar do iOS/Android; instalado como app, a borda é nossa.
       ====================================================================== */
    var pagina = $('.main');
    var dica = document.createElement('div');
    dica.className = 'swipe-hint';
    dica.setAttribute('aria-hidden', 'true');
    dica.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>';
    document.body.appendChild(dica);

    var LIMIAR = 80, BORDA = 24;
    var g = null;   /* gesto em andamento */

    function destinoDoGesto(dx) {
      var voltar = $('.m-header [data-voltar]');
      if (voltar) return dx > 0 ? { tipo: 'back', ir: function () { voltar.click(); } } : null;
      var i = abaAtual(), lista = abas();
      if (i < 0) return null;
      var alvo = lista[i + (dx < 0 ? 1 : -1)];
      if (!alvo) return null;
      return { tipo: dx < 0 ? 'forward' : 'back', ir: function () { location.href = alvo.href; } };
    }

    function soltarPagina(semAnimar) {
      if (!pagina) return;
      pagina.style.transition = semAnimar || reduz.matches ? '' : 'transform 260ms var(--ease-out)';
      pagina.style.transform = '';
      dica.classList.remove('is-on', 'is-pronto');
      dica.style.transform = '';
      dica.style.opacity = '';
    }

    document.addEventListener('touchstart', function (e) {
      g = null;
      if (!celular.matches || e.touches.length !== 1 || !pagina) return;
      if ($('dialog[open]')) return;
      var t = e.touches[0];
      if (!standalone && (t.clientX < BORDA || t.clientX > window.innerWidth - BORDA)) return;
      if (rolaNaHorizontal(e.target)) return;
      g = { x0: t.clientX, y0: t.clientY, t0: e.timeStamp, dx: 0, travado: null, destino: null, pronto: false, ult: [] };
    }, { passive: true });

    document.addEventListener('touchmove', function (e) {
      if (!g) return;
      var t = e.touches[0], dx = t.clientX - g.x0, dy = t.clientY - g.y0;
      if (g.travado === null) {
        if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return;
        g.travado = Math.abs(dx) > Math.abs(dy) * 1.4 ? 'h' : 'v';
        if (g.travado === 'v') { g = null; return; }
        g.destino = destinoDoGesto(dx);
        if (!g.destino) { g = null; return; }
        g.sentido = dx > 0 ? 1 : -1;
        pagina.style.transition = '';
        dica.classList.toggle('swipe-hint--dir', g.sentido < 0);
        dica.classList.add('is-on');
      }
      /* sem preventDefault: o CSS (.main{touch-action:pan-y}) já diz ao navegador que o lateral é nosso, e o ouvinte fica passivo */
      /* só vale no sentido em que o gesto começou; o outro lado "trava" com resistência */
      var util = dx * g.sentido;
      g.dx = util > 0 ? util : util * 0.2;
      g.ult.push({ x: t.clientX, t: e.timeStamp }); if (g.ult.length > 5) g.ult.shift();
      var prog = Math.min(1, g.dx / LIMIAR);
      if (!reduz.matches) pagina.style.transform = 'translateX(' + (g.sentido * Math.min(g.dx, 140) * 0.22).toFixed(1) + 'px)';
      dica.style.opacity = Math.max(0, prog).toFixed(2);
      dica.style.transform = 'translateY(-50%) translateX(' + (g.sentido * (Math.max(0, prog) * 34 - 34)).toFixed(1) + 'px) scale(' + (0.7 + Math.max(0, prog) * 0.3).toFixed(2) + ')';
      var pronto = prog >= 1;
      if (pronto !== g.pronto) { g.pronto = pronto; dica.classList.toggle('is-pronto', pronto); if (pronto) vibrar(6); }
    }, { passive: true });

    function fimDoGesto(e) {
      if (!g || g.travado !== 'h' || !g.destino) { g = null; return; }
      var vel = velocidade(g.ult, 'x', e.timeStamp) * g.sentido;
      var vai = g.dx >= LIMIAR || (vel > VEL_PETELECO && g.dx > 30);
      var destino = g.destino;
      g = null;
      if (!vai) { soltarPagina(); return; }
      vibrar(10);
      guardar('vt-dir', destino.tipo);
      destino.ir();
    }
    document.addEventListener('touchend', fimDoGesto, { passive: true });
    document.addEventListener('touchcancel', function () { if (g) { g = null; soltarPagina(); } }, { passive: true });

    /* ======================================================================
       4. Arrastar pra fechar: popup (bottom sheet, pra baixo) e gaveta (pra esquerda)
       Só no celular. Começa pela alça/cabeçalho, ou pelo corpo quando ele já
       está rolado até o topo (senão o arraste é rolagem do conteúdo).
       ====================================================================== */
    var s = null;
    function podeArrastar(dlg) {
      return dlg && dlg.open && !dlg.hasAttribute('data-obrigatorio') && !dlg.classList.contains('is-closing');
    }
    document.addEventListener('touchstart', function (e) {
      s = null;
      if (!celular.matches || e.touches.length !== 1) return;
      var dlg = e.target.closest('dialog.vt-dialog, dialog.vt-drawer');
      if (!podeArrastar(dlg)) return;
      if (e.target.closest('input, textarea, select, .seg, .pills, [data-no-swipe]')) return;
      var gaveta = dlg.classList.contains('vt-drawer');
      var corpo = e.target.closest('.vt-dialog__body, .vt-drawer__body, nav');
      var t = e.touches[0];
      s = { dlg: dlg, gaveta: gaveta, corpo: corpo, x0: t.clientX, y0: t.clientY, d: 0, travado: null, ult: [] };
    }, { passive: true });

    document.addEventListener('touchmove', function (e) {
      if (!s) return;
      var t = e.touches[0], dx = t.clientX - s.x0, dy = t.clientY - s.y0;
      if (s.travado === null) {
        if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return;
        var principal = s.gaveta ? -dx : dy, cruzado = s.gaveta ? Math.abs(dy) : Math.abs(dx);
        /* sheet: só arrasta pra baixo e, se começou no corpo, só com o corpo no topo */
        if (principal <= 0 || cruzado > Math.abs(principal) || (!s.gaveta && s.corpo && s.corpo.scrollTop > 0)) { s = null; return; }
        s.travado = true;
        s.dlg.style.transition = 'none';
      }
      if (e.cancelable) e.preventDefault();
      var d = s.gaveta ? -dx : dy;
      s.d = d > 0 ? d : d * 0.15;                                   /* pro lado "errado" quase não mexe */
      s.ult.push({ v: s.gaveta ? -t.clientX : t.clientY, t: e.timeStamp }); if (s.ult.length > 5) s.ult.shift();
      s.dlg.style.transform = s.gaveta ? 'translateX(' + (-s.d) + 'px)' : 'translateY(' + s.d + 'px)';
      var tam = s.gaveta ? s.dlg.offsetWidth : s.dlg.offsetHeight;
      s.dlg.style.setProperty('--fundo', String(Math.max(0.15, 1 - s.d / tam)));
    }, { passive: false });

    function limparArraste(dlg) {
      dlg.style.transition = ''; dlg.style.transform = ''; dlg.style.removeProperty('--fundo');
    }
    document.addEventListener('touchend', function (e) {
      if (!s || !s.travado) { s = null; return; }
      var dlg = s.dlg, gaveta = s.gaveta;
      var vel = velocidade(s.ult, 'v', e.timeStamp);
      var tam = gaveta ? dlg.offsetWidth : dlg.offsetHeight;
      var andou = s.d, fecha = andou > tam * 0.3 || (vel > VEL_PETELECO && andou > 20);
      s = null;
      if (!fecha) {
        dlg.style.transition = 'transform 280ms var(--ease-out)';
        dlg.style.transform = '';
        dlg.style.removeProperty('--fundo');
        setTimeout(function () { dlg.style.transition = ''; }, 300);
        return;
      }
      vibrar(8);
      /* sai na velocidade do dedo: quanto mais rápido o peteleco, mais curta a saída */
      var resto = Math.max(0, tam - andou);
      var dur = Math.max(140, Math.min(260, vel > 0 ? resto / (vel * 1.6) : 240));
      dlg.style.transition = 'transform ' + Math.round(dur) + 'ms cubic-bezier(.3,.7,.4,1)';
      dlg.style.transform = gaveta ? 'translateX(-105%)' : 'translateY(105%)';
      dlg.style.setProperty('--fundo', '0');
      var fim = function () { if (dlg.open) dlg.close(); limparArraste(dlg); };
      dlg.addEventListener('transitionend', fim, { once: true });
      setTimeout(fim, dur + 60);
    }, { passive: true });
    document.addEventListener('touchcancel', function () { if (s && s.travado) limparArraste(s.dlg); s = null; }, { passive: true });

    /* ======================================================================
       5. Deslizar o toast pro lado dispensa
       ====================================================================== */
    var tt = null;
    document.addEventListener('pointerdown', function (e) {
      var t = e.target.closest('.toast');
      if (!t || t.classList.contains('is-leaving')) return;
      tt = { el: t, x0: e.clientX, t0: e.timeStamp, dx: 0, id: e.pointerId };
      t.style.transition = 'none';
    });
    document.addEventListener('pointermove', function (e) {
      if (!tt || e.pointerId !== tt.id) return;
      tt.dx = e.clientX - tt.x0;
      tt.el.style.transform = 'translateX(' + tt.dx + 'px)';
      tt.el.style.opacity = String(Math.max(0.2, 1 - Math.abs(tt.dx) / 220));
    });
    function soltarToast(e) {
      if (!tt || (e && e.pointerId !== tt.id)) return;
      var el = tt.el, dx = tt.dx, vel = Math.abs(dx) / Math.max(1, (e ? e.timeStamp : 0) - tt.t0);
      tt = null;
      if (Math.abs(dx) > 70 || (vel > VEL_PETELECO && Math.abs(dx) > 24)) {
        el.style.transition = 'transform 180ms ease-in, opacity 180ms ease-in';
        el.style.transform = 'translateX(' + (dx > 0 ? 120 : -120) + '%)';
        el.style.opacity = '0';
        el.classList.add('is-dispensado');
        setTimeout(function () { el.remove(); }, 200);
      } else {
        el.style.transition = 'transform 240ms var(--ease-out), opacity 240ms var(--ease-out)';
        el.style.transform = ''; el.style.opacity = '';
      }
    }
    document.addEventListener('pointerup', soltarToast);
    document.addEventListener('pointercancel', soltarToast);

    /* ======================================================================
       6. Linhas clicáveis: <tr data-href="...">
       O nome dentro da linha continua sendo um <a> de verdade (teclado, leitor
       de tela, "abrir em nova aba"). Clique em botão/link dentro da linha
       (ex.: WhatsApp) faz só a ação dele.
       ====================================================================== */
    document.addEventListener('click', function (e) {
      var tr = e.target.closest('[data-href]');
      if (!tr || e.defaultPrevented) return;
      if (e.target.closest('a, button, input, select, textarea, label, summary, [data-open]')) return;
      if (window.getSelection && String(window.getSelection()).length) return;   /* estava selecionando texto */
      var destino = tr.getAttribute('data-href');
      if (!/^\/(?!\/)/.test(destino)) return;            /* só caminho interno: data-href nunca leva pra fora nem roda javascript: */
      if (e.metaKey || e.ctrlKey) { window.open(destino, '_blank', 'noopener'); return; }
      iniciarBarra();
      location.href = destino;
    });
    document.addEventListener('auxclick', function (e) {
      var tr = e.target.closest('[data-href]');
      if (tr && e.button === 1 && !e.target.closest('a, button') && /^\/(?!\/)/.test(tr.getAttribute('data-href'))) window.open(tr.getAttribute('data-href'), '_blank', 'noopener');
    });

    /* ======================================================================
       7. Tocar na aba que já está aberta: volta ao topo (padrão Instagram/WhatsApp)
       ====================================================================== */
    document.addEventListener('click', function (e) {
      var a = e.target.closest('.tabbar__item[aria-current="page"]');
      if (!a || window.scrollY < 40) return;
      var url = new URL(a.href, location.href);
      if (url.pathname !== location.pathname) return;            /* subpágina da aba: navega normal */
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: reduz.matches ? 'auto' : 'smooth' });
    });
  }   /* iniciarResto */
})();
