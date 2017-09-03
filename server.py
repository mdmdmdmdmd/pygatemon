import json
import http.server
from socketserver import ThreadingMixIn
import ssl
import time
import uuid
import sqlite3


def get_json(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except:
        return None


def check_json(data):
    try:
        json_data = json.loads(data)
    except:
        return False
    timestamp = json_data.get('timestamp', False)
    uuidstr = json_data.get('uuid', False)
    if not all((timestamp, uuidstr)):
        return False
    if int(timestamp) - int(time.time()) > 90:
        return False
    try:
        uuid.UUID(uuidstr, version=5)
    except ValueError:
        return False
    return True


def store_data(data):
    createtable = 'CREATE TABLE IF NOT EXISTS gatemon (id INTEGER PRIMARY KEY, uuid TEXT, name TEXT, host TEXT, ' \
                  'addrv4 INTEGER, addrv6 INTEGER, dnsv4 INTEGER, dnsv6 INTEGER, ulv4 INTEGER, ulv6 INTEGER)'
    insert = 'INSERT INTO gatemon(uuid, name, host, addrv4, addrv6, dnsv4, dnsv6, ulv4, ulv6) values ' \
             '(?, ?, ? ,? ,? ,? ,? ,? ,?)'
    con = sqlite3.connect('data.db')
    con.row_factory = sqlite3.Row
    json_data = json.loads(data)
    timestamp = json_data['timestamp']
    uuidstr = json_data['uuid']
    name = json_data['name']
    with con:
        con.execute(createtable)
        for host in json_data['hosts']:
            hostname = host['host']
            addrv4 = host['addrv4']
            addrv6 = host['addrv6']
            dnsv4 = host['dnsv4']
            dnsv6 = host['dnsv6']
            ulv4 = host['ulv4']
            ulv6 = host['ulv6']
            try:
                con.execute(insert, (uuidstr, name, hostname, addrv4, addrv6, dnsv4, dnsv6, ulv4, ulv6))
            except:
                return False
    return True


class ThreadingSimpleServer(ThreadingMixIn, http.server.HTTPServer):
    pass


class MyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        tokens = get_json('tokens.json')
        token = self.headers.get('X-gatemon-token')
        if token is None:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'403: No token.')
            return
        if token not in tokens:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'403: Wrong token.')
            return
        content_length = int(self.headers['Content-Length'])
        if content_length < 10:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'400: Malformed POST data?')
            return
        post_data = self.rfile.read(content_length)
        if not check_json(post_data):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'400: Malformed JSON data?')
            return
        if not store_data(post_data):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'400: Error in database.')
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'200: Data stored.')

    def do_GET(self):
        self.send_response(404)
        self.end_headers()
        return

    def do_HEAD(self):
        self.send_response(404)
        self.end_headers()
        return


def main():
    settings = get_json('settings.json')
    if settings is None:
        print('Something is wrong with the settings file.')
        return
    host = settings.get('host')
    port = settings.get('port')
    if not all((host, port)):
        print('Missing host/port settings.')
        return
    server = ThreadingSimpleServer((host, port), MyHandler)
    print('Started http server.')
    try:
        server.socket = ssl.wrap_socket(server.socket, keyfile='key.pem', certfile='cert.pem', server_side=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print('^C received, shutting down server')
        server.socket.close()


if __name__ == '__main__':
    main()
