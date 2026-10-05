/* ==========================================================================
   Vale Tec — digital.js · "Entrar com digital" (passkey / WebAuthn)
   É o mesmo padrão dos bancos e do Google: a digital (ou o rosto) NUNCA sai do celular. O aparelho guarda uma
   chave secreta e só assina um "desafio" que o servidor manda; o servidor confere a assinatura com a chave
   pública que ele guardou no cadastro. Sem senha trafegando, e não dá pra usar num site falso (a chave é presa ao domínio).

   Onde aparece:
     [data-digital-entrar]    botão na tela de login (só se o aparelho tiver leitor de digital/rosto)
     [data-digital-linha]     linha "Seu acesso" nas Configurações (_digital_linha.html), escondida sem leitor
     [data-digital-ativar]    botão "Ativar" (Configurações) — cadastra a digital deste aparelho na conta logada
     #dlg-digital             popup que oferece ativar, UMA vez por aparelho, logo depois de entrar com senha

   Rotas que o backend precisa ter (o mock em _dev/app.py imita todas):
     POST /login/digital/opcoes   -> {challenge, rpId, timeout}                 (desafio novo, guardado na sessão)
     POST /login/digital          <- resposta assinada   -> {ir: "/"}           (confere e faz o login)
     POST /conta/digital/opcoes   -> {challenge, rp, user, ...}                 (só logado)
     POST /conta/digital          <- chave pública nova  -> {ok: true}          (guarda a chave da conta)
   ========================================================================== */
(function () {
  'use strict';
  if (!window.PublicKeyCredential || !navigator.credentials) return;   /* navegador antigo: some tudo, senha continua */

  var csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  var toast = function (m, t) { if (window.VT && window.VT.toast) window.VT.toast(m, t); };

  /* base64url <-> bytes (a WebAuthn fala em ArrayBuffer; o JSON do servidor, em texto) */
  function b64uParaBytes(s) {
    s = s.replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '=';
    var bin = atob(s), out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out.buffer;
  }
  function bytesParaB64u(buf) {
    var b = new Uint8Array(buf), s = '';
    for (var i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function postar(url, corpo) {
    return fetch(url, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(corpo || {})
    }).then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.erro || 'Falhou'); return j; }); });
  }
  /* o usuário cancelou o leitor (ou demorou): não é erro, não grita */
  function cancelou(e) { return e && (e.name === 'NotAllowedError' || e.name === 'AbortError'); }

  var temLeitor = PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable
    ? PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable() : Promise.resolve(false);

  /* ---------- entrar ---------- */
  function entrar(btn) {
    if (btn) { btn.classList.add('is-loading'); btn.setAttribute('aria-disabled', 'true'); }
    return postar('/login/digital/opcoes').then(function (o) {
      return navigator.credentials.get({ publicKey: {
        challenge: b64uParaBytes(o.challenge), rpId: o.rpId, timeout: o.timeout || 60000,
        userVerification: 'required', allowCredentials: []     /* vazio: o aparelho mostra as contas que ele tem pra este site */
      } });
    }).then(function (c) {
      return postar('/login/digital', {
        id: c.id, rawId: bytesParaB64u(c.rawId), type: c.type,
        response: {
          clientDataJSON: bytesParaB64u(c.response.clientDataJSON),
          authenticatorData: bytesParaB64u(c.response.authenticatorData),
          signature: bytesParaB64u(c.response.signature),
          userHandle: c.response.userHandle ? bytesParaB64u(c.response.userHandle) : null
        }
      });
    }).then(function (r) {
      if (navigator.vibrate) { try { navigator.vibrate(10); } catch (_) {} }
      if (r.ir && /^\/(?!\/)/.test(r.ir)) location.href = r.ir;     /* só caminho do próprio sistema */
    }).catch(function (e) {
      if (btn) { btn.classList.remove('is-loading'); btn.removeAttribute('aria-disabled'); }
      if (!cancelou(e)) toast(e.message && e.message !== 'Falhou' ? e.message : 'Não deu para entrar com a digital. Use e-mail e senha.', 'err');
    });
  }

  /* ---------- ativar neste aparelho (logado) ---------- */
  function ativar(btn) {
    if (btn) { btn.classList.add('is-loading'); btn.setAttribute('aria-disabled', 'true'); }
    return postar('/conta/digital/opcoes').then(function (o) {
      return navigator.credentials.create({ publicKey: {
        challenge: b64uParaBytes(o.challenge),
        rp: o.rp,
        user: { id: b64uParaBytes(o.user.id), name: o.user.name, displayName: o.user.displayName },
        pubKeyCredParams: [{ type: 'public-key', alg: -7 }, { type: 'public-key', alg: -257 }],
        authenticatorSelection: { authenticatorAttachment: 'platform', residentKey: 'required', userVerification: 'required' },
        excludeCredentials: (o.excluir || []).map(function (id) { return { type: 'public-key', id: b64uParaBytes(id) }; }),
        timeout: o.timeout || 60000, attestation: 'none'
      } });
    }).then(function (c) {
      return postar('/conta/digital', {
        id: c.id, rawId: bytesParaB64u(c.rawId), type: c.type,
        response: {
          clientDataJSON: bytesParaB64u(c.response.clientDataJSON),
          attestationObject: bytesParaB64u(c.response.attestationObject),
          transports: c.response.getTransports ? c.response.getTransports() : []
        }
      });
    }).then(function () {
      try { localStorage.setItem('vt-digital', 'ativa'); } catch (_) {}
      if (navigator.vibrate) { try { navigator.vibrate([8, 40, 8]); } catch (_) {} }
      toast('Pronto! Da próxima vez, é só tocar em "Entrar com digital".', 'ok');
      document.querySelectorAll('[data-digital-estado]').forEach(function (el) { el.textContent = 'Ativa neste aparelho'; });
      if (btn) { btn.classList.remove('is-loading'); btn.removeAttribute('aria-disabled'); btn.hidden = true; }
      return true;
    }).catch(function (e) {
      if (btn) { btn.classList.remove('is-loading'); btn.removeAttribute('aria-disabled'); }
      if (e && e.name === 'InvalidStateError') { toast('Este aparelho já está cadastrado.', 'ok'); return true; }
      if (!cancelou(e)) toast('Não deu para ativar a digital agora. Tente de novo em Configurações.', 'err');
      return false;
    });
  }

  temLeitor.then(function (ok) {
    if (!ok) return;                               /* sem leitor de digital/rosto: nada aparece, sem promessa falsa */
    document.documentElement.classList.add('tem-digital');
    document.querySelectorAll('[data-digital-linha]').forEach(function (el) { el.hidden = false; });

    document.querySelectorAll('[data-digital-entrar]').forEach(function (caixa) {
      caixa.hidden = false;
      var b = caixa.matches('button') ? caixa : caixa.querySelector('button');
      if (b) b.addEventListener('click', function () { entrar(b); });
    });
    var ativa = false; try { ativa = localStorage.getItem('vt-digital') === 'ativa'; } catch (_) {}
    document.querySelectorAll('[data-digital-ativar]').forEach(function (b) {
      b.hidden = ativa;
      b.addEventListener('click', function () { ativar(b); });
    });
    if (ativa) document.querySelectorAll('[data-digital-estado]').forEach(function (el) { el.textContent = 'Ativa neste aparelho'; });

    /* oferta única logo depois do login com senha (a página marca com data-oferecer-digital) */
    var dlg = document.getElementById('dlg-digital');
    if (dlg && dlg.hasAttribute('data-oferecer') && !ativa) {
      var ja = false; try { ja = !!localStorage.getItem('vt-digital-perguntou'); } catch (_) {}
      if (!ja) {
        try { localStorage.setItem('vt-digital-perguntou', '1'); } catch (_) {}
        /* se outro popup já está na tela (ex.: avisos do dia), espera ele fechar: nunca dois popups de uma vez */
        var oferecer = function () {
          var outro = document.querySelector('dialog[open]');
          if (outro) { outro.addEventListener('close', function () { setTimeout(oferecer, 350); }, { once: true }); return; }
          if (window.VT && window.VT.abrir) window.VT.abrir('dlg-digital');
        };
        setTimeout(oferecer, 900);
      }
      var sim = dlg.querySelector('[data-digital-sim]');
      if (sim) sim.addEventListener('click', function () { ativar(sim).then(function (ok) { if (ok && window.VT) window.VT.fechar('dlg-digital'); }); });
    }
  });
})();
