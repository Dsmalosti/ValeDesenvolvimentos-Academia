"""
Páginas de erro do front novo (templates/errors/403.html, 404.html e 500.html).

[back-04-painel] Criado nesta branch (parte da tarefa 3.7). Antes, um endereço que não existe
mostrava a página branca padrão do Flask, e um erro interno podia mostrar detalhes do código.
As páginas novas não mostram nenhum dado técnico: só o que aconteceu e como voltar.
"""
from flask import render_template

from app.extensions.database import db


def registrar_paginas_de_erro(app):
    """Liga as três páginas de erro no app. Chamado uma vez, no create_app()."""

    @app.errorhandler(403)
    def proibido(erro):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def nao_encontrado(erro):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def erro_interno(erro):
        # desfaz o que estava pela metade no banco, para a próxima requisição começar limpa
        db.session.rollback()
        return render_template('errors/500.html'), 500
