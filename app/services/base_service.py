import logging

from app.extensions.database import db
from app.exceptions import BusinessError

# [back-02-limpeza] log do módulo, no lugar dos print()
logger = logging.getLogger(__name__)


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
        # [back-02-limpeza] antes: print("SALVANDO:", obj), print("ANTES DO COMMIT") e
        # print("DEPOIS DO COMMIT"). Saíram; no lugar, o erro passa a ser registrado no log.
        try:
            db.session.add(obj)
            db.session.commit()
            return obj
        except Exception as erro:
            db.session.rollback()
            # [back-02-limpeza] antes o erro era engolido sem deixar rastro. Só o TIPO do erro e do
            # objeto vão para o log: a mensagem do banco traz os valores (e-mail, CPF), que são
            # dado pessoal e não podem ir para o log (LGPD).
            logger.error("Falha ao salvar %s: %s", type(obj).__name__, type(erro).__name__)
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
