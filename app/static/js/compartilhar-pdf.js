/*
  [back-31-pdf-ficha-avaliacao] Botão "Enviar o PDF": no CELULAR, abre o "Compartilhar" do aparelho com o arquivo
  (WhatsApp, e-mail, Drive...), e a academia escolhe a conversa do aluno. Sem isso, o link só baixa o PDF.

  Uso no template:  <a href="/alunos/1/ficha/pdf" download data-compartilhar-pdf data-arquivo="ficha-ana.pdf"
                       data-texto="Oi Ana! Segue a sua ficha.">Enviar o PDF</a>

  Como funciona:
    - o link é um download normal: sem JavaScript, ou num aparelho sem "Compartilhar arquivo", ele baixa o PDF;
    - em aparelho de toque com suporte, o PDF (poucos KB) é buscado assim que a página abre. É preciso buscar ANTES:
      o iPhone só deixa compartilhar logo depois do toque, sem uma espera de rede no meio;
    - no toque, se o arquivo já chegou, abre o "Compartilhar" em vez de baixar.
*/
(function () {
  'use strict';
  var toque = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
  if (!toque || !navigator.canShare || !window.File) return;

  document.querySelectorAll('a[data-compartilhar-pdf]').forEach(function (link) {
    var arquivo = null;

    fetch(link.href, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.blob() : null; })
      .then(function (blob) {
        if (!blob) return;
        var f = new File([blob], link.getAttribute('data-arquivo') || 'arquivo.pdf', { type: 'application/pdf' });
        if (navigator.canShare({ files: [f] })) arquivo = f;
      })
      .catch(function () { /* sem rede: o link continua baixando */ });

    link.addEventListener('click', function (ev) {
      if (!arquivo) return;                       // ainda não chegou: deixa baixar
      ev.preventDefault();
      navigator.share({ files: [arquivo], text: link.getAttribute('data-texto') || '' })
        .catch(function () { /* a pessoa fechou o "Compartilhar": nada a fazer */ });
    });
  });
})();
