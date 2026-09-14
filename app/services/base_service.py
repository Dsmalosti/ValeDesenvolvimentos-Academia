from flask import current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions.database import db
from app.exceptions import BusinessError


class BaseService:
    """
    Classe base para serviços.
    Contém operações genéricas de persistência.
    """

    @staticmethod
    def salvar(obj):
        """
        Adiciona e commita um objeto no banco
        """
        try:
            db.session.add(obj)
            db.session.commit()
            return obj
        except IntegrityError:
            db.session.rollback()
            current_app.logger.exception("Violação de integridade ao salvar %r", obj)
            raise BusinessError("Já existe um registro com esses dados.")
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Erro ao salvar %r", obj)
            raise BusinessError("Erro ao salvar registro. Tente novamente.")

    @staticmethod
    def deletar(obj):
        """
        Remove e commita um objeto do banco
        """
        try:
            db.session.delete(obj)
            db.session.commit()
            return obj
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Erro ao excluir %r", obj)
            raise BusinessError("Erro ao excluir registro. Tente novamente.")

    @staticmethod
    def commit():
        """
        Commit com rollback automático em caso de erro
        """
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Erro ao salvar alterações")
            raise BusinessError("Erro ao salvar alterações. Tente novamente.")

    @staticmethod
    def rollback():
        """
        Rollback em caso de erro
        """
        db.session.rollback()
