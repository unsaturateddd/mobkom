import http.server
import socketserver
import os

PORT = 8080
APK_DIR = os.path.join(os.path.dirname(__file__), "apk", "app", "build", "outputs", "apk", "debug")


class APKHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=APK_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


def start_download_server():
    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("0.0.0.0", PORT), APKHandler) as httpd:
            print(f"  📥 Сервер загрузки: http://0.0.0.0:{PORT}")
            httpd.serve_forever()
    except OSError as e:
        print(f"  ⚠️ Download server: port {PORT} busy, skipping")
