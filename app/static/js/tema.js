/* ==========================================================================
   Vale Tec — tema.js · claro / escuro / automático
   Carrega no <head>, SEM defer e antes do conteúdo: marca <html data-tema="..."> antes do 1º quadro, senão a tela
   piscaria branca e depois ficaria escura (o "flash" que app ruim tem).
   Preferência por aparelho (localStorage 'vt-tema'): 'auto' (padrão, segue o celular/PC) | 'claro' | 'escuro'.
   Avisa a página com o evento 'vt:tema' (os gráficos se redesenham com as cores novas).
   ========================================================================== */
(function () {
  'use strict';
  var raiz = document.documentElement;
  var pref = 'auto';
  try { pref = localStorage.getItem('vt-tema') || 'auto'; } catch (e) {}
  var mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : { matches: false };

  function aplicar() {
    var escuro = pref === 'escuro' || (pref === 'auto' && mq.matches);
    raiz.setAttribute('data-tema', escuro ? 'escuro' : 'claro');
    try { document.dispatchEvent(new CustomEvent('vt:tema', { detail: { escuro: escuro, pref: pref } })); } catch (e) {}
  }
  aplicar();
  /* "Automático": o celular trocou sozinho (pôr do sol, modo noturno) -> o sistema acompanha na hora */
  var ouvir = function () { if (pref === 'auto') trocar(aplicar); };
  if (mq.addEventListener) mq.addEventListener('change', ouvir); else if (mq.addListener) mq.addListener(ouvir);

  /* troca com transição suave (View Transitions: um "fade" da tela inteira, como no iOS); sem suporte ou com
     movimento reduzido, troca na hora */
  function trocar(fn) {
    var calmo = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (document.startViewTransition && !calmo && document.visibilityState === 'visible') {
      raiz.classList.add('vt-trocando-tema');
      var t = document.startViewTransition(fn);
      t.finished.then(function () { raiz.classList.remove('vt-trocando-tema'); }, function () { raiz.classList.remove('vt-trocando-tema'); });
    } else fn();
  }

  window.VTtema = {
    preferencia: function () { return pref; },
    escuro: function () { return raiz.getAttribute('data-tema') === 'escuro'; },
    definir: function (v) {
      if (['auto', 'claro', 'escuro'].indexOf(v) < 0) return;
      pref = v;
      try { localStorage.setItem('vt-tema', v); } catch (e) {}
      trocar(aplicar);
    }
  };
})();
