"""
[back-18-seguranca] Duas proteções que valem para o sistema inteiro:

  1. LIMITE DE TENTATIVAS (Flask-Limiter): quem tenta adivinhar senha, criar contas em série ou pedir
     troca de senha sem parar é barrado por um tempo, com a resposta 429. Os limites de cada tela
     ficam junto das rotas, em blueprints/auth/routes.py.
  2. CABEÇALHOS DE SEGURANÇA (Flask-Talisman): instruções que o servidor manda ao navegador em toda
     resposta: só carregar script e estilo do próprio sistema (CSP), não deixar a página ser
     embutida em outro site, e, em produção, usar sempre HTTPS.

Antes desta branch não existia nenhuma das duas (as dependências foram autorizadas pelo Diogo, A6).

Onde os contadores de tentativa ficam: por padrão, na memória do processo (`memory://`). Serve para
um servidor com um processo só. Com mais de um processo, cada um conta sozinho e o limite real fica
maior: nesse caso, apontar a variável de ambiente RATELIMIT_STORAGE_URI para um Redis.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# Sem limite padrão: só as rotas marcadas com @limiter.limit(...) são contadas. A chave é o IP de quem chama.
limiter = Limiter(key_func=get_remote_address, default_limits=[])
talisman = Talisman()

# De onde cada tipo de conteúdo pode vir. O front novo não tem script nem evento embutido no HTML: tudo
# sai de /static. As exceções:
#   - style-src 'unsafe-inline': os templates usam o atributo style="..." em muitos lugares;
#   - cdn.jsdelivr.net: só as telas ANTIGAS (base_antigo.html) carregam o Bootstrap de lá. Sai junto com elas;
#   - img-src data: ícones embutidos no CSS;
#   - 'inline-speculation-rules': o app.js do front pede ao navegador para ir carregando a próxima página quando o mouse
#     passa num link (deixa a troca de tela instantânea). Isso é feito com um bloco <script type="speculationrules">
#     criado pelo próprio app.js. A palavra libera SÓ esse tipo de bloco, que não executa código; script comum
#     embutido no HTML continua bloqueado.
CSP = {
    'default-src': "'self'",
    'script-src': ["'self'", "'inline-speculation-rules'", 'https://cdn.jsdelivr.net'],
    'style-src': ["'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net'],
    'img-src': ["'self'", 'data:'],
    'font-src': ["'self'", 'data:'],
    'connect-src': "'self'",
    'object-src': "'none'",
    'base-uri': "'self'",
    'form-action': "'self'",
    'frame-ancestors': "'none'",        # ninguém embute o sistema num iframe (clickjacking)
}


def init_app(app):
    producao = bool(app.config.get('EM_PRODUCAO'))
    limiter.init_app(app)
    # O limite é sempre montado; nos testes automáticos ele só não barra (config.py, LIMITE_DE_TENTATIVAS_LIGADO).
    limiter.enabled = bool(app.config.get('LIMITE_DE_TENTATIVAS_LIGADO', True))
    talisman.init_app(
        app,
        content_security_policy=CSP,
        frame_options='DENY',
        referrer_policy='strict-origin-when-cross-origin',
        # HTTPS obrigatório e cookie só por HTTPS: em produção. No computador de quem desenvolve o endereço é
        # http://localhost, e com isto ligado ninguém conseguiria entrar.
        force_https=producao,
        strict_transport_security=producao,
        session_cookie_secure=producao,
        session_cookie_http_only=True,
    )
