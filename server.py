# -*- coding: utf-8 -*-
"""
«Зертханадан қашу» — жергілікті сервер.
Ойынды (index.html) таратады және телефон-джойстик пен ойын арасында
хабарламаларды жеткізеді (relay). Интернет керек емес — тек бір Wi-Fi.

Іске қосу:  start.bat  (немесе  python server.py)
"""
import http.server, json, os, socket, sys, threading, time, urllib.parse, webbrowser

PORT = 8080
ROOT = os.path.dirname(os.path.abspath(__file__))
LAN_IP = '127.0.0.1'
ROOMS = {}                      # room -> channel -> {'seq': int, 'msgs': [(seq, msg), ...]}
COND = threading.Condition()
KEEP = 300                      # әр арнада сақталатын соңғы хабарламалар саны
POLL = 12.0                     # long-poll күту уақыты (сек)


def channel(room, ch):
    r = ROOMS.setdefault(room, {})
    return r.setdefault(ch, {'seq': 0, 'msgs': []})


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):          # консольді бітемеу үшін
        pass

    def send_json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == '/relay/ping':
            return self.send_json({'ok': True, 'rooms': len(ROOMS), 'host': '%s:%d' % (current_ip(), PORT)})
        if u.path == '/relay/recv':
            room = q.get('room', [''])[0].upper()
            ch = q.get('ch', ['c2h'])[0]
            since = int(q.get('since', ['-1'])[0])
            c = channel(room, ch)
            with COND:
                if since < 0:                       # алғашқы сұраныс: тек ағымдағы нөмірді беру
                    return self.send_json({'seq': c['seq'], 'msgs': []})
                end = time.time() + POLL
                while c['seq'] <= since:
                    left = end - time.time()
                    if left <= 0:
                        break
                    COND.wait(left)
                msgs = [m for s, m in c['msgs'] if s > since]
                return self.send_json({'seq': c['seq'], 'msgs': msgs})
        if u.path == '/':
            self.path = '/index.html'
        return super().do_GET()

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path != '/relay/send':
            return self.send_json({'error': 'not found'}, 404)
        n = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(n).decode('utf-8') or '{}')
        except Exception:
            return self.send_json({'error': 'bad json'}, 400)
        room = q.get('room', [''])[0].upper()
        ch = q.get('ch', ['c2h'])[0]
        msgs = body if isinstance(body, list) else [body]
        c = channel(room, ch)
        with COND:
            for m in msgs:
                c['seq'] += 1
                c['msgs'].append((c['seq'], m))
            if len(c['msgs']) > KEEP:
                del c['msgs'][:len(c['msgs']) - KEEP]
            COND.notify_all()
        return self.send_json({'ok': True, 'seq': c['seq']})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))      # ештеңе жіберілмейді, тек бағыт анықталады
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return '127.0.0.1'


_ip_cache = {'ip': None, 't': 0.0}


def current_ip():
    """Ағымдағы Wi-Fi мекенжайы (желі ауысса да дұрыс болу үшін 5 сек сайын жаңарады)."""
    now = time.time()
    if _ip_cache['ip'] is None or now - _ip_cache['t'] > 5:
        _ip_cache['ip'] = lan_ip()
        _ip_cache['t'] = now
    return _ip_cache['ip']


def main():
    if sys.platform.startswith('win'):
        try:
            os.system('chcp 65001 >nul')
        except Exception:
            pass
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    global LAN_IP
    ip = LAN_IP = lan_ip()
    srv = http.server.ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    srv.daemon_threads = True
    print('=' * 60)
    print('  ЗЕРТХАНАДАН ҚАШУ — сервер іске қосылды')
    print('=' * 60)
    print()
    print('  Панельде / проекторда ашыңыз:   http://%s:%d/' % (ip, PORT))
    print('  (осы компьютерде де сол сілтемені ашыңыз — QR код дұрыс болу үшін)')
    print()
    print('  Телефондар осы Wi-Fi-ға қосылып, ойындағы 📱 батырмасындағы')
    print('  QR кодты сканерлейді.')
    print()
    print('  Тоқтату үшін осы терезені жабыңыз (немесе Ctrl+C).')
    print('=' * 60)
    try:
        webbrowser.open('http://%s:%d/' % (ip, PORT))
    except Exception:
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
