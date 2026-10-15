"""
Envio de e-mail (convite da equipe e troca de senha).

[back-13-equipe] Criado nesta branch. Usa só a biblioteca padrão do Python (smtplib), sem
dependência nova: funciona com qualquer provedor que ofereça SMTP (Gmail, Brevo, Mailgun, o
e-mail do próprio domínio...).

A configuração vem de variáveis de ambiente (ver .env.example):
    SMTP_HOST, SMTP_PORTA (padrão 587), SMTP_USUARIO, SMTP_SENHA, EMAIL_REMETENTE

Enquanto elas não existirem, `email_configurado()` devolve False e NADA é enviado. O sistema não
depende do e-mail para funcionar: o convite tem o botão de copiar o link, e a troca de senha
pode ser gerada pelo comando `flask link-de-senha`.
"""
import os
import smtplib
from email.message import EmailMessage

from flask import current_app


def _config():
    return {chave: (os.environ.get(chave) or '').strip() for chave in
            ('SMTP_HOST', 'SMTP_PORTA', 'SMTP_USUARIO', 'SMTP_SENHA', 'EMAIL_REMETENTE')}


def email_configurado():
    """Há servidor e remetente configurados? (Nos testes automáticos, nunca.)"""
    config = _config()
    return bool(config['SMTP_HOST'] and config['EMAIL_REMETENTE']) and not current_app.config.get('TESTING')


def enviar_email(para, assunto, texto):
    """
    Envia um e-mail de texto simples. Devolve True se o servidor aceitou.
    Nunca levanta erro: uma falha do provedor de e-mail não pode derrubar a tela de quem está
    usando o sistema. O erro vai para o log, sem o endereço do destinatário e sem o texto
    (o texto traz o link de acesso, que é um segredo).
    """
    if not email_configurado():
        return False
    config = _config()
    mensagem = EmailMessage()
    mensagem['From'], mensagem['To'], mensagem['Subject'] = config['EMAIL_REMETENTE'], para, assunto
    mensagem.set_content(texto)
    try:
        with smtplib.SMTP(config['SMTP_HOST'], int(config['SMTP_PORTA'] or 587), timeout=10) as servidor:
            servidor.starttls()                    # nunca manda usuário, senha ou link sem criptografia
            if config['SMTP_USUARIO']:
                servidor.login(config['SMTP_USUARIO'], config['SMTP_SENHA'])
            servidor.send_message(mensagem)
        return True
    except Exception as erro:
        current_app.logger.error('Falha ao enviar e-mail (%s): %s', assunto, type(erro).__name__)
        return False
