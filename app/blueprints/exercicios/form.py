from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, TextAreaField, URLField
from wtforms.validators import DataRequired, Length, Optional, URL

from app.models import GRUPOS_MUSCULARES


class ExercicioForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(message="O nome é obrigatório."), Length(min=2, max=100)])
    grupo_muscular = SelectField(
        'Grupo muscular',
        choices=[('', 'Selecione')] + GRUPOS_MUSCULARES,
        validators=[DataRequired(message="Selecione um grupo muscular.")]
    )
    descricao = TextAreaField('Execução e observações', validators=[Optional(), Length(max=1000)])
    video_url = URLField(
        'Link do vídeo',
        validators=[Optional(), URL(message="Informe uma URL válida."), Length(max=200)]
    )
    ativo = BooleanField('Disponível para novas fichas', default=True)
