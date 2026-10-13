"""
[back-19-lgpd] Dois direitos que a LGPD dá ao ALUNO e que a academia precisa conseguir atender pelo sistema:

  - EXPORTAR: um arquivo com tudo o que o sistema guarda sobre aquele aluno (acesso e portabilidade).
  - APAGAR: eliminar os dados pessoais e de saúde dele.

As duas ações são só do DONO da conta (as rotas conferem).

O que "apagar" faz, e por quê:
  - APAGA de vez: avaliações físicas (feitas e marcadas), fichas de treino, entradas (frequência), sessões da
    agenda e os registros de mensagem;
  - ANONIMIZA o cadastro: nome, e-mail, telefone, CPF, nascimento e observações saem; fica uma linha
    "Aluno removido", inativa, que não aparece mais em nenhuma tela de alunos;
  - MANTÉM cobranças e pagamentos, agora sem nada que identifique a pessoa. O financeiro da academia
    (faturamento do mês, extratos) não pode mudar por causa de um pedido de exclusão, e a lei manda
    guardar registro financeiro. É por isso que a linha do aluno fica: os pagamentos apontam para ela.

Não há como desfazer.
"""
from datetime import datetime

from flask_login import current_user

from app.extensions.database import db
from app.models import (Aluno, AvaliacaoAgendada, AvaliacaoFisica, Cobranca, Ficha, Frequencia, MensagemEnviada, Pagamento, Sessao)

NOME_DO_REMOVIDO = 'Aluno removido'


def _dia(valor):
    """Data ou data e hora em texto ("2026-10-13" / "2026-10-13 14:30"); vazio vira None."""
    if valor is None:
        return None
    return valor.strftime('%Y-%m-%d %H:%M') if isinstance(valor, datetime) else valor.isoformat()


def _numero(valor):
    return float(valor) if valor is not None else None


def _da_conta(modelo, aluno):
    return modelo.query.filter_by(conta_id=current_user.conta_id, aluno_id=aluno.id)


def exportar(aluno):
    """Tudo o que o sistema guarda sobre o aluno, num dicionário pronto para virar arquivo (JSON)."""
    cobrancas = _da_conta(Cobranca, aluno).order_by(Cobranca.data_inicio, Cobranca.id).all()
    avaliacoes = _da_conta(AvaliacaoFisica, aluno).order_by(AvaliacaoFisica.data, AvaliacaoFisica.id).all()
    medidas = ('peso_kg', 'altura_cm', 'imc', 'cintura_cm', 'quadril_cm', 'rcq', 'braco_d_cm', 'coxa_d_cm', 'torax_cm', 'panturrilha_cm',
               'dobra_triceps', 'dobra_subescapular', 'dobra_suprailiaca', 'dobra_abdominal', 'dobra_coxa', 'teste_flexibilidade')
    return {
        'gerado_em': _dia(datetime.now()),
        'origem': f'Vale Tec · {current_user.conta.nome}',
        'cadastro': {
            'nome': aluno.nome, 'email': aluno.email, 'telefone': aluno.telefone, 'cpf': aluno.cpf,
            'data_nascimento': _dia(aluno.data_nascimento), 'cadastrado_em': _dia(aluno.data_cadastro), 'inicio': _dia(aluno.data_inicio),
            'ativo': bool(aluno.ativo), 'plano': aluno.plano.nome if aluno.plano else None, 'dia_vencimento': aluno.dia_vencimento,
            'forma_de_pagamento': aluno.forma_pagamento, 'observacoes': aluno.observacoes,
            'aceita_whatsapp': aluno.aceita_whatsapp,
        },
        'cobrancas': [{
            'tipo': c.tipo, 'plano': c.plano.nome if c.plano else None, 'valor': _numero(c.valor), 'inicio': _dia(c.data_inicio),
            'vencimento': _dia(c.data_vencimento), 'situacao': c.status, 'sessoes': c.quantidade_sessoes,
            'pagamentos': [{'data': _dia(p.data_pagamento), 'forma': p.forma, 'valor': _numero(p.valor_pago)} for p in c.pagamentos],
        } for c in cobrancas],
        'entradas': [_dia(f.data_hora_entrada) for f in _da_conta(Frequencia, aluno).order_by(Frequencia.data_hora_entrada)],
        'fichas_de_treino': [{
            'nome': ficha.nome, 'objetivo': ficha.objetivo, 'criada_em': _dia(ficha.data_criacao), 'em_uso': bool(ficha.ativo),
            'treinos': [{'letra': t.letra, 'nome': t.nome, 'dia': t.dia_semana,
                         'exercicios': [{'exercicio': i.exercicio.nome if i.exercicio else None, 'series': i.series, 'repeticoes': i.repeticoes,
                                         'carga': i.carga, 'descanso': i.descanso} for i in sorted(t.exercicios, key=lambda i: (i.ordem, i.id))]}
                        for t in sorted(ficha.treinos, key=lambda t: (t.letra or 'Z', t.id))],
        } for ficha in Ficha.query.filter_by(aluno_id=aluno.id).order_by(Ficha.id)],
        'avaliacoes_fisicas': [dict(
            {'data': _dia(a.data), 'objetivo': a.objetivo, 'restricoes': a.restricoes, 'medicamentos': a.medicamentos,
             'liberacao_medica': bool(a.liberacao_medica), 'teste_flexao': a.teste_flexao, 'teste_abdominal': a.teste_abdominal, 'anotacao': a.anotacao},
            **{campo: _numero(getattr(a, campo)) for campo in medidas}) for a in avaliacoes],
        'avaliacoes_marcadas': [{'data': _dia(a.data), 'hora': a.hora, 'tipo': a.tipo, 'situacao': a.status}
                                for a in _da_conta(AvaliacaoAgendada, aluno).order_by(AvaliacaoAgendada.data, AvaliacaoAgendada.hora)],
        'sessoes': [{'data': _dia(s.data), 'hora': s.hora, 'duracao_min': s.duracao, 'local': s.local, 'situacao': s.status, 'abateu_do_pacote': bool(s.abateu)}
                    for s in _da_conta(Sessao, aluno).order_by(Sessao.data, Sessao.hora)],
        'mensagens_preparadas': [{'tipo': m.tipo, 'dia': _dia(m.data)} for m in _da_conta(MensagemEnviada, aluno).order_by(MensagemEnviada.data)],
    }


def tem_historico(aluno):
    """O aluno tem cobrança, entrada, avaliação ou sessão? (Se não tem, o cadastro pode simplesmente ser excluído.)"""
    return any(_da_conta(modelo, aluno).first() is not None for modelo in (Cobranca, Frequencia, AvaliacaoFisica, AvaliacaoAgendada, Sessao))


def apagar(aluno):
    """Apaga os dados pessoais e de saúde do aluno e anonimiza o cadastro (ver o texto do começo do arquivo)."""
    for modelo in (AvaliacaoFisica, AvaliacaoAgendada, Frequencia, Sessao, MensagemEnviada):     # as avaliações feitas antes das marcadas (uma aponta para a outra)
        for registro in _da_conta(modelo, aluno).all():
            db.session.delete(registro)
        db.session.flush()
    for ficha in Ficha.query.filter_by(aluno_id=aluno.id).all():        # leva junto os treinos e os exercícios da ficha
        db.session.delete(ficha)
    for pagamento in (Pagamento.query.join(Cobranca, Pagamento.cobranca_id == Cobranca.id)
                      .filter(Cobranca.aluno_id == aluno.id, Pagamento.conta_id == current_user.conta_id).all()):
        pagamento.observacao = None                                      # texto livre: pode ter dado pessoal
    aluno.nome = NOME_DO_REMOVIDO
    aluno.email = aluno.telefone = aluno.cpf = aluno.data_nascimento = aluno.observacoes = None
    aluno.ativo = False
    aluno.acesso_liberado = False
    aluno.aceita_whatsapp = False
    aluno.anonimizado_em = datetime.utcnow()
    db.session.commit()
    return aluno
