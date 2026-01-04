from app.extensions.database import db


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
        db.session.add(obj)
        db.session.commit()
        return obj

    @staticmethod
    def deletar(obj):
        """
        Remove e commita um objeto do banco
        """
        db.session.delete(obj)
        db.session.commit()

    @staticmethod
    def commit():
        """
        Apenas commit (casos específicos)
        """
        db.session.commit()

    @staticmethod
    def rollback():
        """
        Rollback em caso de erro
        """
        db.session.rollback()
