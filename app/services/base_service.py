from app.extensions.database import db
from app.exceptions import BusinessError


class BaseService:
    """
    Classe base para serviços.
    Contém operações genéricas de persistência.
    """

    @staticmethod
    def salvar(obj):
        print("SALVANDO:", obj)

        """
        Adiciona e commita um objeto no banco
        """
        try:
            print("ANTES DO COMMIT")
            db.session.add(obj)
            db.session.commit()
            print("DEPOIS DO COMMIT")
            return obj
        except Exception:
            db.session.rollback()
            raise BusinessError("Erro ao salvar registro")


    @staticmethod
    def deletar(obj):
        """
        Remove e commita um objeto do banco
        """
        try:
            db.session.delete(obj)
            db.session.commit()
            return obj
        except Exception:
            db.session.rollback()
            raise BusinessError("Erro ao excluir registro")

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
