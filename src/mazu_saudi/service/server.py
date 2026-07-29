"""Dependency-free local HTTP server for the MCR-Precip product interface."""

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .forecast import DemoForecastService, ForecastRequest


ASSET_ROOT = Path(__file__).with_name("web")
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
DEFAULT_PORT = 8766


def resolve_asset(request_path: str) -> Path | None:
    relative = "index.html" if request_path == "/" else request_path.lstrip("/")
    candidate = (ASSET_ROOT / relative).resolve()
    if ASSET_ROOT.resolve() not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def dispatch_api(service: DemoForecastService, path: str, query_string: str = ""):
    if path == "/api/v1/health":
        return service.health()
    if path == "/api/v1/config":
        return service.config()
    if path == "/api/v1/events":
        return service.events()
    if path == "/api/v1/forecast":
        query = parse_qs(query_string)
        request = ForecastRequest(
            region=query.get("region", ["arabian_peninsula"])[0],
            lead_hours=int(query.get("lead_hours", [1])[0]),
        )
        return service.forecast(request)
    raise KeyError(path)


def make_handler(service: DemoForecastService | None = None):
    forecast_service = service or DemoForecastService()

    class ProductHandler(BaseHTTPRequestHandler):
        server_version = "MCRPrecipProduct/0.1"

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if parsed.path.startswith("/api/"):
                    try:
                        return self._json(dispatch_api(forecast_service, parsed.path, parsed.query))
                    except KeyError:
                        return self._json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
                return self._asset(parsed.path)
            except (ValueError, TypeError) as exc:
                return self._json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception:
                return self._json({"error": "internal service error"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        def _asset(self, request_path: str):
            candidate = resolve_asset(request_path)
            if candidate is None:
                return self._json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
            body = candidate.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", CONTENT_TYPES.get(candidate.suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload, status=HTTPStatus.OK):
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    return ProductHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the frozen MCR-Precip research prototype")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), make_handler())
    print(f"MCR-Precip product available at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
