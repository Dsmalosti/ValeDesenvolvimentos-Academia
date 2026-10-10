/* ==========================================================================
   Vale Tec — ajustes-iphone.js
   [correcao-iphone 08/10] Complemento do ajustes-iphone.css. Carregado depois do app.js.
   ========================================================================== */
(function () {
  'use strict';
  /* Teclado do iPhone x popup de baixo
     No Safari do iPhone o teclado não encolhe a tela (100dvh continua igual): o popup que fica
     preso embaixo (sheet) ficava atrás do teclado e o botão Salvar sumia. A visualViewport diz
     quanto da tela está visível de verdade; passamos isso pro CSS em --teclado e --vv-h. */
  if (window.visualViewport) {
    var vv = window.visualViewport, raizDoc = document.documentElement;
    var medirTeclado = function () {
      /* com zoom de pinça a área visível também encolhe, mas não é teclado: só mede sem zoom */
      var teclado = Math.abs(vv.scale - 1) < 0.01 ? Math.max(0, window.innerHeight - vv.height - vv.offsetTop) : 0;
      raizDoc.style.setProperty('--teclado', (teclado > 80 ? Math.round(teclado) : 0) + 'px');   /* < 80px é só a barra do Safari */
      raizDoc.style.setProperty('--vv-h', Math.round(vv.height) + 'px');
    };
    vv.addEventListener('resize', medirTeclado);
    vv.addEventListener('scroll', medirTeclado);
    medirTeclado();
    /* campo focado dentro do popup: depois que o teclado sobe, rola o campo pro meio da área visível */
    document.addEventListener('focusin', function (e) {
      var campo = e.target;
      if (!window.matchMedia('(max-width: 991.98px)').matches) return;   /* só celular: no PC o popup fica no meio da tela */
      if (!campo.matches || !campo.matches('input, textarea, select') || !campo.closest('dialog[open]')) return;
      setTimeout(function () { try { campo.scrollIntoView({ block: 'center' }); } catch (_) {} }, 350);
    });
  }
})();
