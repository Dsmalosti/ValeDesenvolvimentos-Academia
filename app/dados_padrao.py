"""
Dados que já vêm com o sistema: o catálogo padrão de exercícios e os modelos de ficha.

[back-14-treinos] Criado nesta branch. É só dado (listas), sem nenhuma regra: quem usa são o
services/treino_service.py, o comando `flask semear-catalogo` e a migration da back-14, que
grava o catálogo no banco.

Os nomes e os modelos são os do front (vale-tec-front/_dev). Os modelos apontam para os
exercícios PELO NOME: por isso o nome de um exercício do catálogo padrão não deve ser trocado.
"""

GRUPOS = ['Peito', 'Costas', 'Pernas', 'Ombros', 'Bíceps', 'Tríceps', 'Abdômen']

# (nome, grupo muscular, equipamento)
EXERCICIOS_PADRAO = [
    ('Supino reto', 'Peito', 'Barra'), ('Crucifixo inclinado', 'Peito', 'Halteres'), ('Puxada frontal', 'Costas', 'Polia alta'),
    ('Remada curvada', 'Costas', 'Barra'), ('Agachamento livre', 'Pernas', 'Barra'), ('Leg press 45', 'Pernas', 'Máquina'),
    ('Desenvolvimento', 'Ombros', 'Halteres'), ('Rosca direta', 'Bíceps', 'Barra W'),
    ('Supino inclinado', 'Peito', 'Halteres'), ('Crossover', 'Peito', 'Polia'), ('Flexão de braços', 'Peito', 'Peso do corpo'),
    ('Peck deck', 'Peito', 'Máquina'), ('Supino declinado', 'Peito', 'Barra'), ('Voador', 'Peito', 'Máquina'),
    ('Pulldown', 'Costas', 'Polia'), ('Remada baixa', 'Costas', 'Polia'), ('Remada unilateral', 'Costas', 'Halteres'),
    ('Barra fixa', 'Costas', 'Peso do corpo'), ('Levantamento terra', 'Costas', 'Barra'), ('Serrote', 'Costas', 'Halteres'),
    ('Extensora', 'Pernas', 'Máquina'), ('Flexora deitada', 'Pernas', 'Máquina'), ('Stiff', 'Pernas', 'Barra'),
    ('Afundo', 'Pernas', 'Halteres'), ('Agachamento búlgaro', 'Pernas', 'Halteres'), ('Panturrilha em pé', 'Pernas', 'Máquina'),
    ('Cadeira abdutora', 'Pernas', 'Máquina'), ('Elevação pélvica', 'Pernas', 'Barra'), ('Hack squat', 'Pernas', 'Máquina'),
    ('Elevação lateral', 'Ombros', 'Halteres'), ('Elevação frontal', 'Ombros', 'Halteres'), ('Desenvolvimento Arnold', 'Ombros', 'Halteres'),
    ('Remada alta', 'Ombros', 'Barra'), ('Crucifixo inverso', 'Ombros', 'Máquina'), ('Encolhimento', 'Ombros', 'Halteres'),
    ('Rosca alternada', 'Bíceps', 'Halteres'), ('Rosca martelo', 'Bíceps', 'Halteres'), ('Rosca scott', 'Bíceps', 'Barra W'),
    ('Rosca concentrada', 'Bíceps', 'Halteres'), ('Rosca na polia', 'Bíceps', 'Polia'), ('Rosca inversa', 'Bíceps', 'Barra W'),
    ('Tríceps pulley', 'Tríceps', 'Polia'), ('Tríceps testa', 'Tríceps', 'Barra W'), ('Tríceps francês', 'Tríceps', 'Halteres'),
    ('Mergulho no banco', 'Tríceps', 'Peso do corpo'), ('Tríceps corda', 'Tríceps', 'Polia'), ('Tríceps coice', 'Tríceps', 'Halteres'),
    ('Supino fechado', 'Tríceps', 'Barra'), ('Extensão de tríceps', 'Tríceps', 'Polia'),
    ('Abdominal supra', 'Abdômen', 'Peso do corpo'), ('Prancha', 'Abdômen', 'Peso do corpo'), ('Abdominal infra', 'Abdômen', 'Peso do corpo'),
    ('Abdominal na polia', 'Abdômen', 'Polia'), ('Elevação de pernas', 'Abdômen', 'Peso do corpo'), ('Russian twist', 'Abdômen', 'Anilha'),
    ('Roda abdominal', 'Abdômen', 'Roda'), ('Prancha lateral', 'Abdômen', 'Peso do corpo'),
    ('Panturrilha sentado', 'Pernas', 'Máquina'), ('Adução de quadril', 'Pernas', 'Máquina'), ('Passada', 'Pernas', 'Halteres'),
    ('Face pull', 'Ombros', 'Polia'), ('Pullover', 'Costas', 'Halteres'), ('Remada cavalinho', 'Costas', 'Máquina'),
    ('Crucifixo reto', 'Peito', 'Halteres'),
]

# Músculos mais exigidos em cada grupo, do principal para o de apoio (a tela do exercício mostra
# as barras; o número é só o tamanho da barra, não uma medida).
MUSCULOS_DO_GRUPO = {
    'Peito': [('Peitoral', 90), ('Tríceps', 55), ('Ombro', 35)], 'Costas': [('Dorsal', 88), ('Bíceps', 50), ('Trapézio', 40)],
    'Pernas': [('Quadríceps', 85), ('Glúteos', 60), ('Posterior', 45)], 'Ombros': [('Deltoide', 90), ('Trapézio', 45), ('Tríceps', 30)],
    'Bíceps': [('Bíceps', 92), ('Antebraço', 45), ('Braquial', 40)], 'Tríceps': [('Tríceps', 92), ('Ombro', 30), ('Peitoral', 25)],
    'Abdômen': [('Reto abdominal', 90), ('Oblíquos', 50), ('Lombar', 25)],
}

COMO_EXECUTAR_PADRAO = ('Ajuste a posição inicial com o corpo estável e a coluna neutra. Faça o movimento de forma controlada, sem usar '
                        'impulso, e volte devagar até a posição de partida. Respire soltando o ar no esforço. Se sentir dor articular, '
                        'reduza a carga e chame o instrutor.')


def _t(nome, *itens):
    """Um treino do modelo: nome e a lista (exercício, séries, repetições)."""
    return {'nome': nome, 'itens': list(itens)}


# Modelos prontos de ficha. `chave` é o que fica gravado na ficha criada a partir do modelo
# (coluna ficha.modelo), para contar quantas vezes cada um foi usado. `min` = duração aproximada.
MODELOS = [
    {'id': 1, 'chave': 'hipertrofia', 'nome': 'Hipertrofia', 'sub': 'A/B/C · 6 exercícios por treino', 'icone': 'dumbbell', 'tom': 'blue', 'min': 48, 'treinos': {
        'A': _t('Peito, costas e braço', ('Supino reto', 4, 10), ('Crucifixo inclinado', 3, 12), ('Puxada frontal', 4, 10), ('Remada curvada', 3, 12), ('Tríceps corda', 3, 15), ('Rosca direta', 3, 12)),
        'B': _t('Pernas e ombros', ('Agachamento livre', 4, 10), ('Leg press 45', 3, 12), ('Extensora', 3, 15), ('Stiff', 3, 12), ('Desenvolvimento', 3, 10), ('Elevação lateral', 3, 15)),
        'C': _t('Costas, bíceps e abdômen', ('Levantamento terra', 4, 8), ('Pulldown', 3, 12), ('Remada baixa', 3, 12), ('Rosca martelo', 3, 12), ('Abdominal supra', 3, 20), ('Prancha', 3, 1))}},
    {'id': 2, 'chave': 'perda-de-peso', 'nome': 'Perda de peso', 'sub': 'A/B · força + aeróbico', 'icone': 'trend', 'tom': 'orange', 'min': 55, 'treinos': {
        'A': _t('Corpo inteiro', ('Agachamento livre', 3, 15), ('Supino reto', 3, 15), ('Puxada frontal', 3, 15), ('Prancha', 3, 1)),
        'B': _t('Circuito de força', ('Leg press 45', 3, 15), ('Remada baixa', 3, 15), ('Desenvolvimento', 3, 15), ('Abdominal infra', 3, 20))}},
    {'id': 3, 'chave': 'condicionamento', 'nome': 'Condicionamento', 'sub': 'Futebol e esportes de campo', 'icone': 'play', 'tom': 'teal', 'min': 50, 'treinos': {
        'A': _t('Potência e base', ('Agachamento búlgaro', 3, 10), ('Stiff', 3, 10), ('Panturrilha em pé', 4, 15), ('Prancha lateral', 3, 1))}},
    {'id': 4, 'chave': 'baixo-impacto', 'nome': 'Baixo impacto', 'sub': 'Exige liberação médica no cadastro', 'icone': 'check', 'tom': 'green', 'min': 40, 'treinos': {
        'A': _t('Mobilidade e força leve', ('Leg press 45', 2, 15), ('Remada baixa', 2, 15), ('Elevação pélvica', 2, 15))}},
    {'id': 5, 'chave': 'iniciante', 'nome': 'Iniciante', 'sub': 'Primeiro mês de academia', 'icone': 'users', 'tom': 'slate', 'min': 40, 'treinos': {
        'A': _t('Adaptação A', ('Leg press 45', 2, 12), ('Supino reto', 2, 12), ('Puxada frontal', 2, 12), ('Prancha', 2, 1)),
        'B': _t('Adaptação B', ('Extensora', 2, 12), ('Desenvolvimento', 2, 12), ('Remada baixa', 2, 12), ('Abdominal supra', 2, 15))}},
]
