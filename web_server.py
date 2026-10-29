"""Servidor simples para executar o site separado da API FastAPI."""
from argparse import ArgumentParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

RAIZ = Path(__file__).resolve().parent
PAGINAS = {
    "/": "/web/index.html",
    "/login": "/web/login.html",
    "/dashboard": "/web/dashboard.html",
    "/sensors": "/web/sensors.html",
    "/inspection": "/web/inspection.html",
}


class SiteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(RAIZ), **kwargs)

    def translate_path(self, path):
        rota = unquote(urlsplit(path).path)
        if rota in PAGINAS:
            rota = PAGINAS[rota]
        elif rota.startswith("/static/"):
            rota = "/web/" + rota.removeprefix("/static/")
        return super().translate_path(rota)


def main():
    parser = ArgumentParser(description="Servidor local das páginas VulcanTech")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5500)
    args = parser.parse_args()
    servidor = ThreadingHTTPServer((args.host, args.port), SiteHandler)
    print(f"Site VulcanTech em http://{args.host}:{args.port} (Ctrl+C para encerrar)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor do site encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
