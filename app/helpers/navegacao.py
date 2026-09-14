from urllib.parse import urlparse


def url_segura(destino):
    """Aceita apenas caminhos internos (evita open redirect via ?next=)."""
    if not destino:
        return False
    destino = destino.strip()
    if not destino.startswith("/") or destino.startswith("//") or "\\" in destino:
        return False
    url = urlparse(destino)
    return not url.scheme and not url.netloc
