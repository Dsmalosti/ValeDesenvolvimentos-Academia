"""
[back-34-auditoria-front] O que os BUSCADORES (Google e os buscadores com IA) leem do Vale Tec.

Antes não existia nada disto. A auditoria de 17/10/2026 (skill auditoria-qualidade-web) achou: sem robots.txt, sem
sitemap.xml, nenhuma página com descrição, canonical ou dados estruturados, e as telas internas sem "não indexar".

  GET /robots.txt   o que o buscador pode visitar, e onde está o sitemap
  GET /sitemap.xml  as páginas PÚBLICAS (entrar, criar conta, termos, privacidade)
  GET /llms.txt     resumo do Vale Tec em texto simples, para buscadores com IA (fatos: o que é, para quem, preço, quem oferece)

E, em toda resposta:
  - telas públicas: `seo` no template (descrição, endereço canônico, Open Graph e, no login, os dados estruturados JSON-LD);
  - todo o resto (telas internas, links de convite e de troca de senha, PDFs): cabeçalho `X-Robots-Tag: noindex`, para
    nenhuma tela de dentro aparecer no Google, nem se alguém publicar um link dela.

Os dados da empresa são os mesmos dos termos de uso (app/legal/). Mudou lá, muda aqui.
"""
from flask import Blueprint, Response, request, url_for

from app.models import CONTA_PERSONAL
from app.services import assinatura_service

seo_blueprint = Blueprint('seo', __name__)

EMPRESA = {
    'nome': 'Vale Tec',
    'razao_social': '60.499.733 ADAUTO RODRIGUES DOS SANTOS NETTO',
    'cnpj': '60.499.733/0001-44',
    'cidade': 'Tremembé', 'uf': 'SP',
}

# Telas que o buscador pode mostrar: endpoint -> (complemento do título, descrição). A descrição é o texto que aparece
# embaixo do link no resultado da busca: 120 a 160 caracteres, escrita para gente, sem exagero.
PUBLICAS = {
    'auth.login': ('gestão de academias e personal trainers',
                   'Sistema online para academias, estúdios e personal trainers: alunos, mensalidades, check-in, fichas '
                   'de treino e avaliações no celular. 2 meses grátis.'),
    'auth.criar_conta': ('2 meses grátis para sua academia',
                         'Crie a conta do Vale Tec em 1 minuto e use grátis por 2 meses. Alunos, cobranças, frequência e '
                         'fichas de treino da sua academia, direto do celular.'),
    'legal.termos': ('',
                     'Termos de uso do Vale Tec: teste grátis, preços, pagamento por PIX, cancelamento e como tratamos os '
                     'dados dos alunos da sua academia ou do seu estúdio.'),
    'legal.privacidade': ('',
                          'Política de privacidade do Vale Tec: quais dados tratamos, para quê, com quem compartilhamos, por '
                          'quanto tempo guardamos e como exercer seus direitos.'),
}
# Respostas que não são telas (o próprio robots.txt, os arquivos estáticos, o monitor) não levam o cabeçalho
SEM_CABECALHO = {'static', 'seo.robots', 'seo.sitemap', 'seo.llms', 'saude.saude'}


def _site():
    """Endereço do site (https://dominio/), como o visitante chegou. Atrás do proxy do Render, o ProxyFix acerta o https."""
    return request.url_root


def _dados_estruturados():
    """JSON-LD do login (a porta de entrada): quem oferece e o que é, com os preços. O template escreve com |tojson."""
    site = _site()
    precos = assinatura_service.PRECOS
    return {
        '@context': 'https://schema.org',
        '@graph': [
            {'@type': 'Organization', '@id': site + '#empresa', 'name': EMPRESA['nome'], 'legalName': EMPRESA['razao_social'],
             'taxID': EMPRESA['cnpj'], 'url': site, 'email': assinatura_service.contato()['email'],
             'address': {'@type': 'PostalAddress', 'addressLocality': EMPRESA['cidade'], 'addressRegion': EMPRESA['uf'],
                         'addressCountry': 'BR'}},
            {'@type': 'SoftwareApplication', 'name': 'Vale Tec', 'url': site, 'applicationCategory': 'BusinessApplication',
             'operatingSystem': 'Web (navegador do celular ou do computador)', 'inLanguage': 'pt-BR',
             'publisher': {'@id': site + '#empresa'},
             'offers': [{'@type': 'Offer', 'name': 'Academia ou estúdio, por mês', 'price': str(precos['academia']), 'priceCurrency': 'BRL'},
                        {'@type': 'Offer', 'name': 'Personal trainer, por mês', 'price': str(precos[CONTA_PERSONAL]), 'priceCurrency': 'BRL'}]},
        ],
    }


@seo_blueprint.app_context_processor
def seo_da_tela():
    """`seo` = {complemento, descricao, canonical, jsonld} nas telas públicas; vazio nas outras (o template não escreve nada)."""
    dados = PUBLICAS.get(request.endpoint)
    if not dados:
        return {'seo': {}}
    complemento, descricao = dados
    return {'seo': {'complemento': complemento, 'descricao': descricao,
                    'canonical': url_for(request.endpoint, _external=True),
                    'jsonld': _dados_estruturados() if request.endpoint == 'auth.login' else None}}


@seo_blueprint.after_app_request
def nao_indexar_o_que_e_de_dentro(resposta):
    if request.endpoint not in PUBLICAS and request.endpoint not in SEM_CABECALHO:
        resposta.headers.setdefault('X-Robots-Tag', 'noindex, nofollow')
    return resposta


@seo_blueprint.route('/robots.txt')
def robots():
    linhas = [
        'User-agent: *',
        # áreas que não interessam a buscador (as telas internas já pedem login e mandam o robô para a tela de entrar)
        'Disallow: /admin',
        'Disallow: /convite/',
        'Disallow: /nova-senha/',
        '',
        f"Sitemap: {url_for('seo.sitemap', _external=True)}",
    ]
    return Response('\n'.join(linhas) + '\n', mimetype='text/plain')


@seo_blueprint.route('/sitemap.xml')
def sitemap():
    enderecos = ''.join(f'<url><loc>{url_for(endpoint, _external=True)}</loc></url>' for endpoint in PUBLICAS)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{enderecos}</urlset>')
    return Response(xml, mimetype='application/xml')


@seo_blueprint.route('/llms.txt')
def llms():
    """Fatos do Vale Tec em Markdown simples. Proposta aberta (llmstxt.org) que alguns buscadores com IA leem."""
    a = assinatura_service
    reais = a._reais
    # o preço de lançamento (back-28): o desconto sobre a tabela, igual para todas as contas
    promo = (f"- Preço de lançamento, com {a.DESCONTO_DE_LANCAMENTO}% de desconto sobre a tabela "
             f"({reais(a.PRECOS_DE_TABELA['academia'])} e {reais(a.PRECOS_DE_TABELA[CONTA_PERSONAL])}), para todas as contas.\n"
             ) if a.DESCONTO_DE_LANCAMENTO else ''
    texto = f"""# Vale Tec

> Sistema online de gestão para academias, estúdios e personal trainers, feito no Brasil. Funciona no navegador do celular ou do computador, sem instalar nada.

## Para quem é
- Academias e estúdios: dono, recepção e instrutores, cada um com o acesso do seu papel.
- Personal trainers: pacotes de sessões, saldo de cada aluno e agenda.

## O que faz
- Cadastro de alunos, planos e mensalidades; quem está em dia e quem está atrasado.
- Cobrança, renovação, diária avulsa e extrato de pagamentos.
- Check-in e frequência, com ranking de presença do mês.
- Fichas de treino e avaliação física, com PDF para mandar ao aluno.
- Mensagens prontas para o WhatsApp (lembrete de vencimento, aniversário, cobrança).
- Relatórios de faturamento, custos e retenção.

## Preço
- Teste grátis de 2 meses, sem cartão.
- Academia ou estúdio: {reais(a.PRECOS['academia'])} por mês. Personal trainer: {reais(a.PRECOS[CONTA_PERSONAL])} por mês. Pagamento por PIX.
{promo}
## Quem oferece
- {EMPRESA['razao_social']}, CNPJ {EMPRESA['cnpj']}, {EMPRESA['cidade']}/{EMPRESA['uf']}, Brasil.
- Contato: {a.contato()['email']}

## Links
- [Criar conta]({url_for('auth.criar_conta', _external=True)})
- [Entrar]({url_for('auth.login', _external=True)})
- [Termos de uso]({url_for('legal.termos', _external=True)})
- [Política de privacidade]({url_for('legal.privacidade', _external=True)})
"""
    return Response(texto, mimetype='text/plain')
