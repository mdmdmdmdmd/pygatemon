import json
import http.server
from socketserver import ThreadingMixIn
import ssl
import time
import uuid
import sqlite3


def get_settings():
    try:
        with open('settings.json', 'r') as file:
            return json.load(file)
    except:
        return None


def get_tokens():
    try:
        with open('tokens.json', 'r') as file:
            return json.load(file)
    except:
        return None


def handle_json(data):
    try:
        json_data = json.loads(data)
    except:
        return False
    timestamp = json_data.get('timestamp', False)
    if not timestamp:
        return False
    if int(timestamp) - int(time.time()) > 90:
        return False
    uuidstr = json_data.get('uuid', False)
    if not uuidstr:
        return False
    try:
        uuid.UUID(uuidstr, version=5)
    except ValueError:
        return False
    return True


class ThreadingSimpleServer(ThreadingMixIn, http.server.HTTPServer):
    pass


class MyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        if content_length < 10:
            self.send_response(400)
            self.wfile.write(b'400: Malformed POST data?')
            return
        post_data = self.rfile.read(content_length)
        if not handle_json(post_data):
            self.send_response(400)
            self.wfile.write(b'400: Malformed JSON data?')
            return
        self.send_response(200)
        self.wfile.write(b'200: Data stored.')

    def do_GET(self):
        self.send_response(404)
        return

    def do_HEAD(self):
        self.send_response(404)
        return


def main():
    settings = get_settings()
    if settings is None:
        print('Something is wrong with the settings file.')
        return
    host = settings.get('host')
    port = settings.get('port')
    if not all((host, port)):
        print('Missing host/port settings.')
        return
    server = ThreadingSimpleServer((host, port), MyHandler)
    print('Started http server')
    try:
        server.socket = ssl.wrap_socket(server.socket, keyfile='key.pem', certfile='cert.pem', server_side=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print('^C received, shutting down server')
        server.socket.close()


if __name__ == '__main__':
    main()