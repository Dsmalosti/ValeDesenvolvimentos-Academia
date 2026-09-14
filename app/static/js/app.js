/*
 * Interações do painel (sem dependências). Tudo é melhoria progressiva:
 * sem JavaScript os formulários continuam funcionando.
 */
(() => {
  "use strict";

  const $$ = (seletor, raiz = document) => Array.from(raiz.querySelectorAll(seletor));

  // ===== Menu lateral no mobile =====
  const sidebar = document.querySelector("[data-sidebar]");
  const overlay = document.querySelector("[data-sidebar-overlay]");
  const botaoMenu = document.querySelector("[data-sidebar-open]");

  function alternarSidebar(aberta) {
    if (!sidebar) return;
    sidebar.classList.toggle("-translate-x-full", !aberta);
    overlay?.classList.toggle("opacity-0", !aberta);
    overlay?.classList.toggle("pointer-events-none", !aberta);
    botaoMenu?.setAttribute("aria-expanded", String(aberta));
    document.body.classList.toggle("overflow-hidden", aberta);
    if (aberta) sidebar.querySelector("a, button")?.focus();
  }

  botaoMenu?.addEventListener("click", () => alternarSidebar(true));
  overlay?.addEventListener("click", () => alternarSidebar(false));
  $$("[data-sidebar-close]").forEach((botao) => botao.addEventListener("click", () => alternarSidebar(false)));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && botaoMenu?.getAttribute("aria-expanded") === "true") {
      alternarSidebar(false);
      botaoMenu.focus();
    }
  });

  // ===== Notificações (flash) =====
  $$("[data-toast]").forEach((toast, indice) => {
    const fechar = () => {
      toast.style.transition = "opacity 180ms ease, transform 180ms ease";
      toast.style.opacity = "0";
      toast.style.transform = "translateY(-6px)";
      setTimeout(() => toast.remove(), 200);
    };
    const tempo = toast.getAttribute("role") === "alert" ? 9000 : 5000 + indice * 400;
    let timer = setTimeout(fechar, tempo);

    toast.querySelector("[data-toast-fechar]")?.addEventListener("click", fechar);
    toast.addEventListener("mouseenter", () => clearTimeout(timer));
    toast.addEventListener("mouseleave", () => {
      timer = setTimeout(fechar, 2500);
    });
  });

  // ===== Confirmação de ações destrutivas =====
  const dialogo = document.getElementById("dialogo-confirmacao");
  let formularioPendente = null;

  document.addEventListener("submit", (evento) => {
    const form = evento.target;
    if (!(form instanceof HTMLFormElement) || !form.dataset.confirmar) return;
    if (form.dataset.confirmado === "1") return;

    evento.preventDefault();

    if (!dialogo || typeof dialogo.showModal !== "function") {
      if (window.confirm(form.dataset.confirmar)) enviarConfirmado(form);
      return;
    }

    formularioPendente = form;
    const neutro = form.dataset.confirmarTom === "neutro";
    const botao = dialogo.querySelector("[data-dialogo-confirmar]");
    dialogo.querySelector("[data-dialogo-titulo]").textContent = form.dataset.confirmarTitulo || "Tem certeza?";
    dialogo.querySelector("[data-dialogo-texto]").textContent = form.dataset.confirmar;
    dialogo.querySelector("[data-dialogo-icone]").classList.toggle("hidden", neutro);
    botao.textContent = form.dataset.confirmarBotao || "Confirmar";
    botao.classList.toggle("btn-perigo", !neutro);
    botao.classList.toggle("btn-escuro", neutro);
    dialogo.showModal();
  });

  dialogo?.addEventListener("close", () => {
    if (dialogo.returnValue === "confirmar" && formularioPendente) {
      enviarConfirmado(formularioPendente);
    }
    formularioPendente = null;
  });

  function enviarConfirmado(form) {
    form.dataset.confirmado = "1";
    if (typeof form.requestSubmit === "function") form.requestSubmit();
    else form.submit();
  }

  // ===== Evita envio duplicado =====
  document.addEventListener("submit", (evento) => {
    if (evento.defaultPrevented) return;
    const botao = evento.submitter;
    if (!botao || evento.target.method.toLowerCase() !== "post") return;
    // desabilita depois do envio para o valor do botão (ex.: acao=salvar_e_novo) ir junto
    setTimeout(() => {
      botao.disabled = true;
      botao.setAttribute("aria-busy", "true");
    }, 0);
  });

  window.addEventListener("pageshow", () => {
    $$("button[aria-busy='true']").forEach((botao) => {
      botao.disabled = false;
      botao.removeAttribute("aria-busy");
    });
    $$("form[data-confirmado]").forEach((form) => delete form.dataset.confirmado);
  });

  // ===== Seleção em massa =====
  $$("[data-lote]").forEach((raiz) => {
    const formId = raiz.dataset.lote;
    const form = document.getElementById(formId);
    const todos = raiz.querySelector("[data-lote-todos]");
    const barra = document.querySelector(`[data-lote-barra="${formId}"]`);
    const contador = barra?.querySelector("[data-lote-contador]");
    const itens = () => $$("[data-lote-item]", raiz);

    function atualizar() {
      const total = itens().length;
      const marcados = itens().filter((item) => item.checked).length;
      if (todos) {
        todos.checked = marcados > 0 && marcados === total;
        todos.indeterminate = marcados > 0 && marcados < total;
      }
      barra?.classList.toggle("hidden", marcados === 0);
      if (contador) contador.textContent = marcados === 1 ? "1 selecionado" : `${marcados} selecionados`;
      if (form) {
        form.dataset.confirmar =
          `Excluir ${marcados} aluno(s)? As fichas de treino desses alunos também serão excluídas. Essa ação não pode ser desfeita.`;
      }
    }

    todos?.addEventListener("change", () => {
      itens().forEach((item) => {
        item.checked = todos.checked;
      });
      atualizar();
    });
    raiz.addEventListener("change", (evento) => {
      if (evento.target.matches("[data-lote-item]")) atualizar();
    });
    atualizar();
  });

  // ===== Mostrar/ocultar senha =====
  $$("[data-alternar-senha]").forEach((botao) => {
    const input = document.getElementById(botao.getAttribute("aria-controls"));
    if (!input) return;
    botao.addEventListener("click", () => {
      const mostrar = input.type === "password";
      input.type = mostrar ? "text" : "password";
      botao.setAttribute("aria-pressed", String(mostrar));
      botao.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
      botao.querySelector("[data-icone-mostrar]")?.classList.toggle("hidden", mostrar);
      botao.querySelector("[data-icone-ocultar]")?.classList.toggle("hidden", !mostrar);
    });
  });

  // ===== Máscaras de CPF e telefone =====
  const mascaras = {
    cpf(d) {
      d = d.slice(0, 11);
      let r = d.slice(0, 3);
      if (d.length > 3) r += "." + d.slice(3, 6);
      if (d.length > 6) r += "." + d.slice(6, 9);
      if (d.length > 9) r += "-" + d.slice(9);
      return r;
    },
    telefone(d) {
      d = d.slice(0, 11);
      if (!d) return "";
      if (d.length <= 2) return "(" + d;
      const corte = d.length > 10 ? 7 : 6;
      let r = `(${d.slice(0, 2)}) ${d.slice(2, corte)}`;
      if (d.length > corte) r += "-" + d.slice(corte);
      return r;
    },
  };

  $$("[data-mascara]").forEach((input) => {
    const aplicar = mascaras[input.dataset.mascara];
    if (!aplicar) return;
    const formatar = () => {
      input.value = aplicar(input.value.replace(/\D/g, ""));
    };
    input.addEventListener("input", (evento) => {
      if (evento.inputType && evento.inputType.startsWith("delete")) return;
      formatar();
    });
    input.addEventListener("blur", formatar);
    if (input.value) formatar();
  });

  // ===== Atalhos de preenchimento (ex.: duração do plano) =====
  $$("[data-preencher]").forEach((botao) => {
    botao.addEventListener("click", () => {
      const alvo = document.getElementById(botao.dataset.preencher);
      if (!alvo) return;
      alvo.value = botao.dataset.valor;
      alvo.dispatchEvent(new Event("input", { bubbles: true }));
      alvo.focus();
    });
  });

  // ===== Imprimir ficha =====
  $$("[data-imprimir]").forEach((botao) => botao.addEventListener("click", () => window.print()));
})();
