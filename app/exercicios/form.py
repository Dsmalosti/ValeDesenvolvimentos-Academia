from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, DateField, BooleanField, SelectField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional, URL


class ExercicioForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(message="O nome é obrigatório."), Length(min=2, max=100)])
    grupo_muscular = SelectField(
        'Grupo Muscular',
        choices=[
            ('peito', 'Peito'),
            ('costas', 'Costas'),
            ('ombro', 'Ombros'),
            ('biceps', 'Bíceps'),
            ('triceps', 'Tríceps'),
            ('pernas', 'Pernas'),
            ('gluteo', 'Glúteo'),
            ('abdomen', 'Abdômen'),
            ('outro', 'Outro')
        ],
        validators=[DataRequired(message="Selecione um grupo muscular.")]
    )
    descricao = TextAreaField('Descrição / Observações', validators=[Optional()])
    video_url = StringField(
        'URL do Vídeo (opcional)',
        validators=[Optional(), URL(message="Informe uma URL válida.")]
    )
    ativo = BooleanField('Ativo', default=True)