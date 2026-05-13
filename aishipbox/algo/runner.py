"""Runner script executed in the user's virtual environment."""

import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


PROCESS_BASE_STUB = '''
class ProcessBase:
    def __init__(self, url: str = ""):
        self.url = url
'''


def create_handler(processor):
    """Create HTTP handler with processor instance."""

    class AlgoHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                params = json.loads(body)
                result, status_code = processor.process(params)

                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
            except Exception as e:
                logger.exception("Error processing request")
                self.send_error(500, str(e))

        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
            else:
                self.send_error(404, "Not Found")

    return AlgoHandler


def main():
    # Read configuration from environment
    service_dir = Path(os.environ["ALGO_SERVICE_DIR"]).resolve()
    host = os.environ["ALGO_HOST"]
    port = int(os.environ["ALGO_PORT"])
    debug = os.environ.get("ALGO_DEBUG") == "1"
    debug_port = int(os.environ.get("ALGO_DEBUG_PORT", "5678"))

    service_name = service_dir.name

    if debug:
        try:
            import debugpy
            debugpy.listen(("0.0.0.0", debug_port))
            logger.info(f"Debugger listening on port {debug_port}")
            logger.info("Waiting for VS Code to attach (press F5)...")
            debugpy.wait_for_client()
            logger.info("Debugger attached")
        except ImportError:
            logger.error("debugpy not installed. Install it with: pip install debugpy")
            return 1

    # Inject ProcessBase stub into rest.process_base
    import types
    rest_module = types.ModuleType("rest")
    process_base_module = types.ModuleType("rest.process_base")
    exec(PROCESS_BASE_STUB, process_base_module.__dict__)
    rest_module.process_base = process_base_module
    sys.modules["rest"] = rest_module
    sys.modules["rest.process_base"] = process_base_module

    # Add parent directory to path for absolute imports
    sys.path.insert(0, str(service_dir.parent))

    try:
        # Import as package to match production environment
        import importlib
        main_module = importlib.import_module(f"{service_name}.main")
        AlgoProcessor = main_module.AlgoProcessor
    except ImportError as e:
        logger.error(f"Error importing AlgoProcessor: {e}")
        return 1

    processor = AlgoProcessor()
    handler = create_handler(processor)

    try:
        server = HTTPServer((host, port), handler)
    except OSError as e:
        if e.errno == 48:  # Address already in use
            logger.error(f"Port {port} is already in use.")
            logger.error(f"Try: algo run --port {port + 1}")
            return 1
        raise

    logger.info(f"Starting server at http://{host}:{port}")
    logger.info(f"POST http://{host}:{port}/  - Process request")
    logger.info(f"GET  http://{host}:{port}/health - Health check")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
