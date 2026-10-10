"""Testes da branch back-05-repo-e-config: variáveis de ambiente que o app exige para subir."""
import logging

import pytest

from app import create_app


@pytest.fixture()
def ambiente(monkeypatch):
    """Devolve o monkeypatch já sem nenhuma das variáveis de banco, para cada teste definir a sua."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URI", raising=False)
    return monkeypatch


def test_sobe_com_database_url(ambiente):
    ambiente.setenv("DATABASE_URL", "sqlite:///:memory:")
    assert create_app().config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_nome_antigo_ainda_funciona_mas_avisa(ambiente, caplog):
    ambiente.setenv("DATABASE_URI", "sqlite:///:memory:")
    with caplog.at_level(logging.WARNING):
        app = create_app()

    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert "DATABASE_URI mudou de nome para DATABASE_URL" in caplog.text


def test_nome_novo_vence_o_antigo(ambiente):
    ambiente.setenv("DATABASE_URL", "sqlite:///:memory:")
    ambiente.setenv("DATABASE_URI", "sqlite:///outro.db")
    assert create_app().config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_nao_sobe_sem_banco(ambiente):
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app()


def test_nao_sobe_sem_secret_key(ambiente):
    ambiente.setenv("DATABASE_URL", "sqlite:///:memory:")
    ambiente.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_secret_key_nao_tem_valor_padrao_no_codigo(ambiente):
    """Antes o config.py trazia "chave-dev" como padrão: uma chave pública, que está no GitHub."""
    import importlib

    import config

    ambiente.delenv("SECRET_KEY", raising=False)
    try:
        importlib.reload(config)             # relê o config.py como se a variável não existisse
        assert config.Config.SECRET_KEY is None
    finally:
        ambiente.undo()                      # devolve as variáveis de teste
        importlib.reload(config)             # e deixa o módulo como estava para os outros testes
