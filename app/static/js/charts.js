/* ==========================================================================
   Vale Tec — charts.js
   Gráficos em SVG puro (sem biblioteca). Regras do design system:
   sem pizza; toda série tem tabela acessível (.visually-hidden); a cor sai
   dos tokens CSS (getComputedStyle), nunca de hex solto; meta em --yellow-chart.

   Uso no HTML:
     <div class="chart" data-chart="linha" data-json='{"labels":[...],"valores":[...],"meta":250,"unidade":"alunos"}'></div>
     tipos: linha | barras
   Opções: meta, unidade, prefixo, destaque (índice da barra), altura, rotulo-final (bool)
           link (só linha): URL aberta ao clicar no gráfico — no toque, o 1º toque mostra o balão e o 2º no mesmo ponto abre
           linkRotulo: texto da ação no balão ("ver alunos ativos")
           metaPct (só linha): o balão mostra também quanto o ponto representa da meta (ex.: "94% da meta")
           delta (padrão true): o balão mostra a variação contra o ponto anterior (▲ +6 vs Ago); menorMelhor inverte a cor
   Interação (padrão em todo gráfico): mouse passa e o ponto/barra cresce e acende; no toque, arrastar o dedo de lado
   percorre os meses; teclado: setas/Home/End/Enter/Esc com o foco no gráfico.
   O Flask só precisa serializar o dict com |tojson.
   ========================================================================== */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var css = function (n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); };
  var el = function (tag, attrs, txt) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (txt != null) e.textContent = txt;
    return e;
  };
  var fmtNum = function (v, o) {
    var s = Number(v).toLocaleString('pt-BR', { maximumFractionDigits: o.casas != null ? o.casas : 0, minimumFractionDigits: o.casas || 0 });
    return (o.prefixo || '') + s + (o.sufixo || '');
  };

  /* escala "bonita": arredonda min/max para passos redondos */
  function escala(min, max, n) {
    if (min === max) { min -= 1; max += 1; }
    var span = max - min, passo = Math.pow(10, Math.floor(Math.log10(span / n)));
    var m = span / n / passo;
    passo *= m > 5 ? 10 : m > 2 ? 5 : m > 1 ? 2 : 1;
    var lo = Math.floor(min / passo) * passo, hi = Math.ceil(max / passo) * passo, t = [];
    for (var v = lo; v <= hi + passo / 2; v += passo) t.push(+v.toFixed(6));
    return { lo: lo, hi: hi, ticks: t };
  }

  function tabelaAcessivel(host, o) {
    var t = document.createElement('table');
    // a classe vai num <div> em volta: <table> ignora width:1px e "vazava" pra fora da tela (rolagem lateral no celular)
    var caixa = document.createElement('div');
    caixa.className = 'visually-hidden';
    caixa.appendChild(t);
    var cap = document.createElement('caption');
    cap.textContent = o.titulo || 'Dados do gráfico';
    t.appendChild(cap);
    /* montado com textContent, nunca com HTML: rótulo pode vir do banco (nome de plano/aluno) e virar XSS */
    var celula = function (tag, txt, scope) { var c = document.createElement(tag); c.textContent = txt; if (scope) c.scope = scope; return c; };
    var thead = t.createTHead().insertRow();
    thead.appendChild(celula('th', 'Período', 'col'));
    thead.appendChild(celula('th', o.unidade || 'Valor', 'col'));
    var tbody = t.createTBody();
    o.labels.forEach(function (l, i) {
      var tr = tbody.insertRow();
      tr.appendChild(celula('th', l, 'row'));
      tr.appendChild(celula('td', fmtNum(o.valores[i], o)));
    });
    host.appendChild(caixa);
  }

  function desenhar(host) {
    var o;
    try { o = JSON.parse(host.getAttribute('data-json')); } catch (e) { return; }
    var tipo = host.getAttribute('data-chart');
    var W = Math.max(280, Math.round(host.clientWidth || host.parentNode.clientWidth));
    var H = o.altura || (W < 520 ? 190 : 250);
    var pad = { t: 18, r: o.rotuloFinal === false ? 14 : (W < 520 ? 48 : 58), b: 26, l: 40 };
    var iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
    var n = o.valores.length;

    var todos = o.valores.slice();
    if (o.meta != null) todos.push(o.meta);
    var min = Math.min.apply(null, todos), max = Math.max.apply(null, todos);
    if (tipo === 'barras') min = Math.min(0, min);
    var esc = escala(min, max, 4);
    var y = function (v) { return pad.t + ih - ((v - esc.lo) / (esc.hi - esc.lo)) * ih; };
    var stepX = tipo === 'barras' ? iw / n : iw / Math.max(1, n - 1);
    var x = function (i) { return tipo === 'barras' ? pad.l + stepX * i + stepX / 2 : pad.l + stepX * i; };

    host.innerHTML = '';
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': (o.titulo || 'Gráfico') + '. Os dados completos estão na tabela logo abaixo.' });
    var grid = css('--grid'), faint = css('--text-faint'), azul = css('--blue'), amarelo = css('--yellow-chart'), soft = css('--text-soft');

    esc.ticks.forEach(function (t) {
      svg.appendChild(el('line', { x1: pad.l, x2: W - pad.r, y1: y(t), y2: y(t), stroke: grid, 'stroke-width': 1 }));
      svg.appendChild(el('text', { x: pad.l - 8, y: y(t) + 4, 'text-anchor': 'end', 'font-size': 11, 'font-weight': 600, fill: faint }, fmtNum(t, o)));
    });

    /* rótulos do eixo X: no máximo ~6 para não colidir */
    var salto = o.todosRotulos && W >= 520 ? 1 : Math.ceil(n / (W < 520 ? 5 : 8));
    o.labels.forEach(function (l, i) {
      if (i % salto !== 0 && i !== n - 1) return;
      svg.appendChild(el('text', { x: x(i), y: H - 6, 'text-anchor': 'middle', 'font-size': 11, 'font-weight': 600, fill: faint }, l));
    });

    var tip = document.createElement('div');
    tip.className = 'chart-tip';
    tip.setAttribute('aria-hidden', 'true');
    var calmo = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ---- balão: o VALOR manda (grande), o rótulo vem depois; variação contra o ponto anterior com seta
       (▲/▼ + sinal: não depende só da cor) e % da meta. Tudo com textContent: rótulo pode vir do banco. ---- */
    var toqueAtivo = false;   /* último ponteiro foi toque? muda o texto da ação ("toque de novo" x "clique") */
    function linhaTip(cls, txt) { var e = document.createElement('span'); e.className = cls; e.textContent = txt; tip.appendChild(e); return e; }
    function mostrarTip(i) {
      tip.textContent = '';
      var unid = o.unidade === 'reais' ? '' : (o.unidade && !o.prefixo ? ' ' + o.unidade : '');
      var rs = o.unidade === 'reais' && !o.prefixo ? 'R$ ' : '';
      linhaTip('chart-tip__val', rs + fmtNum(o.valores[i], o) + unid);
      linhaTip('chart-tip__lbl', o.labels[i]);
      if (i > 0 && o.delta !== false) {
        var dv = o.valores[i] - o.valores[i - 1];
        var sobe = dv > 0, igual = dv === 0;
        var bom = o.menorMelhor ? !sobe : sobe;
        linhaTip('chart-tip__delta ' + (igual ? '' : (bom ? 'is-bom' : 'is-ruim')),
          (igual ? '= ' : (sobe ? '▲ +' : '▼ −')) + rs + fmtNum(Math.abs(dv), o) + ' vs ' + o.labels[i - 1]);
      }
      if (o.meta && o.metaRotulo) {   /* linha de referência que não é meta (ex.: média): diz quanto acima/abaixo */
        var dm = o.valores[i] - o.meta;
        linhaTip('chart-tip__meta', dm === 0 ? 'na ' + o.metaRotulo : rs + fmtNum(Math.abs(Math.round(dm)), o) + (dm > 0 ? ' acima' : ' abaixo') + ' da ' + o.metaRotulo);
      } else if (o.meta && (o.metaPct || tipo === 'barras')) linhaTip('chart-tip__meta', Math.round(o.valores[i] / o.meta * 100) + '% da meta');
      if (o.link) linhaTip('chart-tip__acao', (toqueAtivo ? 'toque de novo para ' : 'clique para ') + (o.linkRotulo || 'ver detalhes') + ' ›');
      /* balão não vaza pela borda do card: centraliza no ponto, mas encosta no limite se precisar */
      var hw = host.clientWidth || W, px = x(i) / W * hw, meia = (tip.offsetWidth || 0) / 2;
      tip.style.left = (meia ? Math.max(meia, Math.min(hw - meia, px)) : px) + 'px';
      tip.style.top = (tipo === 'barras' ? Math.min(y(o.valores[i]), base0) : y(o.valores[i])) / H * 100 + '%';
      tip.classList.add('on');
    }
    var base0 = y(Math.max(0, esc.lo));

    var marcar, limpar;   /* cada tipo diz como destacar o índice i (e desfazer) */
    var stepHit = stepX;

    if (tipo === 'linha') {
      var pts = o.valores.map(function (v, i) { return [x(i), y(v)]; });
      var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
      var area = d + ' L' + pts[n - 1][0] + ',' + (pad.t + ih) + ' L' + pts[0][0] + ',' + (pad.t + ih) + ' Z';
      svg.appendChild(el('path', { d: area, fill: azul, opacity: 0.09 }));
      /* "acende" a área até o mês apontado (o resto fica no tom normal): mostra o caminho até ali */
      var cid = 'vtc' + Math.random().toString(36).slice(2, 8);
      var defs = el('defs', {}), clip = el('clipPath', { id: cid }), clipR = el('rect', { x: pad.l, y: 0, width: 0, height: H });
      clip.appendChild(clipR); defs.appendChild(clip); svg.appendChild(defs);
      var areaLuz = el('path', { d: area, fill: azul, opacity: 0, 'clip-path': 'url(#' + cid + ')', 'class': 'chart-luz' });
      svg.appendChild(areaLuz);
      if (o.meta != null) {
        svg.appendChild(el('line', { x1: pad.l, x2: W - pad.r, y1: y(o.meta), y2: y(o.meta), stroke: amarelo, 'stroke-width': 1.6, 'stroke-dasharray': '5 4' }));
        svg.appendChild(el('text', { x: W - pad.r, y: y(o.meta) - 7, 'text-anchor': 'end', 'font-size': 11, 'font-weight': 700, fill: css('--yellow-ink') }, 'meta ' + fmtNum(o.meta, o)));
      }
      var linha = el('path', { d: d, fill: 'none', stroke: azul, 'stroke-width': 2.2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });
      svg.appendChild(linha);
      if (!calmo && linha.getTotalLength && !host._desenhado) {
        var len = linha.getTotalLength();
        linha.style.strokeDasharray = len; linha.style.strokeDashoffset = len;
        linha.getBoundingClientRect();
        linha.style.transition = 'stroke-dashoffset 900ms cubic-bezier(.16,1,.3,1)';
        requestAnimationFrame(function () { linha.style.strokeDashoffset = 0; });
      }
      var fim = null;
      if (o.rotuloFinal !== false) {
        svg.appendChild(el('circle', { cx: pts[n - 1][0], cy: pts[n - 1][1], r: 4.5, fill: azul, stroke: css('--card'), 'stroke-width': 2 }));
        fim = el('text', { x: pts[n - 1][0] + 10, y: pts[n - 1][1] + 4, 'font-size': 13, 'font-weight': 700, fill: css('--text'), 'class': 'chart-fim' }, fmtNum(o.valores[n - 1], o));
        svg.appendChild(fim);
      }
      /* guia vertical: deixa claro qual mês está sob o dedo/mouse */
      var guia = el('line', { y1: pad.t, y2: pad.t + ih, stroke: css('--blue-300'), 'stroke-width': 1, 'stroke-dasharray': '3 3', opacity: 0 });
      svg.insertBefore(guia, linha);
      /* ponto em foco: cresce (halo + miolo) — o "aumentar" do pedido; transform/opacity só, com transição curta */
      var focoG = el('g', { 'class': 'chart-foco' });
      var halo = el('circle', { r: 11, fill: azul, opacity: 0.16, 'class': 'chart-foco__halo' });
      var foco = el('circle', { r: 5.5, fill: azul, stroke: css('--card'), 'stroke-width': 2.5, 'class': 'chart-foco__miolo' });
      focoG.appendChild(halo); focoG.appendChild(foco); svg.appendChild(focoG);
      marcar = function (i) {
        focoG.style.transform = 'translate(' + x(i) + 'px,' + y(o.valores[i]) + 'px)'; focoG.classList.add('on');
        guia.setAttribute('x1', x(i)); guia.setAttribute('x2', x(i)); guia.setAttribute('opacity', 1);
        clipR.setAttribute('width', Math.max(0, x(i) - pad.l)); areaLuz.setAttribute('opacity', 0.14);
        if (fim) fim.setAttribute('opacity', i === n - 1 ? 0 : 0.35);
      };
      limpar = function () { focoG.classList.remove('on'); guia.setAttribute('opacity', 0); areaLuz.setAttribute('opacity', 0); if (fim) fim.setAttribute('opacity', 1); };
    } else {
      var bw = Math.min(34, stepX * 0.62);
      var g = el('g', { 'class': 'chart-bars' + (calmo || host._desenhado ? '' : ' is-entrando') });
      var barras = o.valores.map(function (v, i) {
        var top = y(v), destaque = o.destaque === i;
        var r = el('rect', { 'class': 'b', x: x(i) - bw / 2, y: Math.min(top, base0), width: bw, height: Math.max(2, Math.abs(base0 - top)), rx: 5, fill: destaque ? (o.destaqueCor === 'amarelo' ? amarelo : css('--blue')) : css('--blue-300') });
        r.style.animationDelay = (i * 28) + 'ms';
        g.appendChild(r);
        return r;
      });
      svg.appendChild(g);
      if (g.classList.contains('is-entrando')) setTimeout(function () { g.classList.remove('is-entrando'); }, 900);   /* depois da entrada, o hover manda no transform */
      if (o.meta != null) {
        svg.appendChild(el('line', { x1: pad.l, x2: W - pad.r, y1: y(o.meta), y2: y(o.meta), stroke: o.metaCor === 'neutra' ? soft : amarelo, 'stroke-width': 1.6, 'stroke-dasharray': '5 4' }));
        if (o.metaRotulo) svg.appendChild(el('text', { x: W - pad.r, y: y(o.meta) - 6, 'text-anchor': 'end', 'font-size': 11, 'font-weight': 700, fill: soft, 'paint-order': 'stroke', stroke: css('--card'), 'stroke-width': 3 }, o.metaRotulo + ' ' + fmtNum(o.meta, o)));
      }
      var rotDestaque = null;
      if (o.destaque != null && o.rotuloDestaque !== false) { rotDestaque = el('text', { x: x(o.destaque), y: y(o.valores[o.destaque]) - 7, 'text-anchor': 'middle', 'font-size': 12, 'font-weight': 800, fill: css('--text') }, fmtNum(o.valores[o.destaque], o)); svg.appendChild(rotDestaque); }
      marcar = function (i) {
        g.classList.add('has-ativo');
        barras.forEach(function (b, k) { b.classList.toggle('is-ativo', k === i); });
        if (rotDestaque) rotDestaque.setAttribute('opacity', 0.35);   /* o valor apontado vai no balão */
      };
      limpar = function () {
        g.classList.remove('has-ativo'); barras.forEach(function (b) { b.classList.remove('is-ativo'); });
        if (rotDestaque) rotDestaque.setAttribute('opacity', 1);
      };
    }

    /* ---- uma camada de ponteiro para os dois tipos: o alvo é a coluna inteira (bem maior que o ponto/barra) ----
       mouse: passa e mostra · toque: toca e mostra, ARRASTA o dedo de lado e o balão acompanha (como app de banco/bolsa),
       2º toque no mesmo ponto abre o link · teclado: setas/Home/End, Enter abre, Esc fecha. */
    var alvo = el('rect', { x: pad.l - (tipo === 'barras' ? 0 : stepHit / 2), y: pad.t - 10, width: iw + (tipo === 'barras' ? 0 : stepHit), height: ih + 10, fill: 'transparent', 'class': 'chart-alvo' });
    if (o.link) { alvo.style.cursor = 'pointer'; host.classList.add('chart--link'); }
    svg.appendChild(alvo);
    var atual = -1, armado = -1, abrir = false, arrastando = false, moveu = false;
    var indice = function (ev) {
      var r = svg.getBoundingClientRect();
      var px = ((ev.clientX - r.left) / r.width) * W;
      var k = tipo === 'barras' ? Math.floor((px - pad.l) / stepX) : Math.round((px - pad.l) / stepX);
      return Math.max(0, Math.min(n - 1, k));
    };
    function ir(i) {
      if (i === atual && tip.classList.contains('on')) return;
      if (atual !== -1 && i !== atual && toqueAtivo && navigator.vibrate) { try { navigator.vibrate(4); } catch (_) {} }   /* "clique" leve a cada mês, no dedo */
      atual = i; marcar(i); mostrarTip(i);
    }
    var esconder = function () { limpar(); tip.classList.remove('on'); atual = armado = -1; };
    alvo.addEventListener('pointermove', function (ev) {
      if (ev.pointerType === 'mouse') { toqueAtivo = false; ir(indice(ev)); }
      else if (arrastando) { var k = indice(ev); if (k !== atual) moveu = true; ir(k); }
    });
    alvo.addEventListener('pointerdown', function (ev) {
      toqueAtivo = ev.pointerType !== 'mouse';
      var i = indice(ev);
      abrir = !toqueAtivo || (armado === i && tip.classList.contains('on'));   /* toque: 2º toque no mesmo ponto abre */
      armado = i; atual = -1; moveu = false; ir(i);
      if (toqueAtivo) { arrastando = true; try { alvo.setPointerCapture(ev.pointerId); } catch (_) {} }
    });
    var soltar = function (ev) { if (ev.pointerType !== 'mouse') { arrastando = false; if (moveu) { armado = atual; abrir = false; } } };
    alvo.addEventListener('pointerup', soltar);
    alvo.addEventListener('pointercancel', function (ev) { soltar(ev); });   /* rolagem vertical tomou o gesto: balão fica onde estava */
    /* mouse saiu: some o balão. No toque o balão fica até tocar fora (senão sumiria ao levantar o dedo) */
    alvo.addEventListener('pointerleave', function (ev) { if (ev.pointerType === 'mouse') esconder(); });
    if (host._fora) document.removeEventListener('pointerdown', host._fora);   /* redesenho (resize) não acumula ouvintes */
    host._fora = function (ev) { if (!svg.contains(ev.target)) esconder(); };
    document.addEventListener('pointerdown', host._fora, { passive: true });
    var abrirLink = function () { if (o.link && /^\/(?!\/)/.test(o.link)) location.href = o.link; };   /* só caminho do próprio sistema */
    alvo.addEventListener('click', function () {
      if (!o.link || !abrir) return;
      if (navigator.vibrate && toqueAtivo) { try { navigator.vibrate(8); } catch (_) {} }
      abrirLink();
    });
    /* teclado: o próprio contêiner recebe foco (os mesmos detalhes do mouse; a tabela continua pro leitor de tela) */
    host.tabIndex = 0;
    host.setAttribute('role', 'group');
    host.setAttribute('aria-label', (o.titulo || 'Gráfico') + ': use as setas para ver cada ponto' + (o.link ? ', Enter abre' : ''));
    host.onkeydown = function (ev) {
      var k = ev.key, i = atual === -1 ? n - 1 : atual;
      if (k === 'ArrowRight') i = Math.min(n - 1, atual === -1 ? n - 1 : i + 1);
      else if (k === 'ArrowLeft') i = Math.max(0, atual === -1 ? n - 1 : i - 1);
      else if (k === 'Home') i = 0; else if (k === 'End') i = n - 1;
      else if (k === 'Escape') { esconder(); return; }
      else if (k === 'Enter' && o.link) { abrirLink(); return; }
      else return;
      ev.preventDefault(); toqueAtivo = false; ir(i);
    };
    host.onfocus = function () { if (host.matches(':focus-visible')) { toqueAtivo = false; ir(atual === -1 ? n - 1 : atual); } };
    host.onblur = esconder;
    host.appendChild(svg);
    host.appendChild(tip);
    tabelaAcessivel(host, o);
    host._desenhado = true;   /* redesenho por resize não repete a animação de entrada */
  }

  function iniciar() {
    var hosts = Array.prototype.slice.call(document.querySelectorAll('[data-chart]'));
    hosts.forEach(function (h) {
      desenhar(h);
      var ultimo = h.clientWidth;
      if ('ResizeObserver' in window) {
        new ResizeObserver(function () {
          if (Math.abs(h.clientWidth - ultimo) > 8) { ultimo = h.clientWidth; desenhar(h); }
        }).observe(h);
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar); else iniciar();
  /* trocou claro/escuro (tema.js): redesenha com as cores novas dos tokens (sem repetir a animação de entrada) */
  document.addEventListener('vt:tema', function () {
    Array.prototype.forEach.call(document.querySelectorAll('[data-chart]'), function (h) { if (h._desenhado) desenhar(h); });
  });

  /* ==========================================================================
     Gráficos feitos em HTML (barra empilhada, mapa de calor, linhas de plano)
     [data-dica="texto"]      passa o mouse (ou toca, se não for link) e aparece um balão com o texto
     [data-seg-grupo] + [data-seg="id"]  segmento da barra e linha da lista com o mesmo id acendem JUNTOS
                                          (passa na linha "Mensal" -> o pedaço Mensal da barra cresce e os outros apagam)
     ========================================================================== */
  var dica = document.createElement('div');
  dica.className = 'dica'; dica.setAttribute('aria-hidden', 'true');
  var dicaDe = null;
  function mostrarDica(alvo) {
    if (!dica.isConnected) document.body.appendChild(dica);
    dica.textContent = alvo.getAttribute('data-dica');            /* texto puro: pode ter nome de plano vindo do banco */
    var r = alvo.getBoundingClientRect(), meia = dica.offsetWidth / 2, vw = document.documentElement.clientWidth;
    dica.style.left = Math.max(8 + meia, Math.min(vw - 8 - meia, r.left + r.width / 2)) + 'px';
    dica.style.top = r.top + 'px';
    dica.classList.add('on'); dicaDe = alvo;
  }
  function esconderDica() { dica.classList.remove('on'); dicaDe = null; }
  function acender(el, on) {
    var grupo = el.closest('[data-seg-grupo]'); if (!grupo) return;
    var id = el.getAttribute('data-seg');
    grupo.classList.toggle('has-seg', on);
    Array.prototype.forEach.call(grupo.querySelectorAll('[data-seg]'), function (x) { x.classList.toggle('is-seg', on && x.getAttribute('data-seg') === id); });
  }
  document.addEventListener('pointerover', function (ev) {
    if (ev.pointerType !== 'mouse') return;
    var d = ev.target.closest('[data-dica]'); if (d && d !== dicaDe) mostrarDica(d);
    var s = ev.target.closest('[data-seg]'); if (s) acender(s, true);
  });
  document.addEventListener('pointerout', function (ev) {
    if (ev.pointerType !== 'mouse') return;
    var d = ev.target.closest('[data-dica]'); if (d && !d.contains(ev.relatedTarget)) esconderDica();
    var s = ev.target.closest('[data-seg]'); if (s && !s.contains(ev.relatedTarget)) acender(s, false);
  });
  /* toque: no que NÃO é link, tocar mostra o balão (fica até tocar em outro lugar); link continua abrindo direto */
  document.addEventListener('pointerdown', function (ev) {
    if (ev.pointerType === 'mouse') return;
    var d = ev.target.closest('[data-dica]');
    if (d && !d.closest('a[href]')) { mostrarDica(d); return; }
    esconderDica();
  }, { passive: true });
  /* teclado: foco numa linha de plano acende o pedaço dela na barra */
  document.addEventListener('focusin', function (ev) { var s = ev.target.closest && ev.target.closest('[data-seg]'); if (s) acender(s, true); });
  document.addEventListener('focusout', function (ev) { var s = ev.target.closest && ev.target.closest('[data-seg]'); if (s) acender(s, false); });
  window.addEventListener('scroll', esconderDica, { passive: true });
})();
