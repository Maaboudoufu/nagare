"""Browser terminals: a WebSocket (RFC 6455, standard library only) bridged to a pseudo-terminal running
`docker exec` / `docker attach` into the user's own container (workspace.py):
  project  a shell in the user's workspace (CLI lessons: aws, git, go...), in the folder they chose.
  sandbox  the user's Learn Linux sandbox for the lesson.
Typing counts as activity, so an open terminal someone is using keeps its container alive.
"""
import base64, fcntl, hashlib, json, os, pty, signal, socket, struct, subprocess, termios, threading

import workspace

WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


# ---- WebSocket framing ----

def _frame(opcode, payload=b''):
    n = len(payload)
    head = bytes([0x80 | opcode])
    if n < 126:
        head += bytes([n])
    elif n < 65536:
        head += bytes([126]) + struct.pack('>H', n)
    else:
        head += bytes([127]) + struct.pack('>Q', n)
    return head + payload


def _read_exact(rfile, n):
    data = b''
    while len(data) < n:
        chunk = rfile.read(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def _read_frame(rfile):
    """(opcode, payload) of the next client frame, or (None, None) once the connection is gone."""
    head = _read_exact(rfile, 2)
    if not head:
        return None, None
    n = head[1] & 0x7F
    if n == 126:
        n = struct.unpack('>H', _read_exact(rfile, 2))[0]
    elif n == 127:
        n = struct.unpack('>Q', _read_exact(rfile, 8))[0]
    mask = _read_exact(rfile, 4) if head[1] & 0x80 else b'\0\0\0\0'
    data = _read_exact(rfile, n) or b''
    if n:  # unmask in one big-integer XOR instead of a slow per-byte loop
        m = (mask * (n // 4 + 1))[:n]
        data = (int.from_bytes(data, 'big') ^ int.from_bytes(m, 'big')).to_bytes(n, 'big')
    return head[0] & 0x0F, data


def _handshake(handler):
    key = handler.headers.get('Sec-WebSocket-Key')
    if not key or handler.headers.get('Upgrade', '').lower() != 'websocket':
        handler.send_error(400, 'WebSocket only')
        return False
    handler.protocol_version = 'HTTP/1.1'  # RFC 6455 requires it; Firefox drops an HTTP/1.0 101, Chrome doesn't care
    handler.send_response(101, 'Switching Protocols')
    handler.send_header('Upgrade', 'websocket')
    handler.send_header('Connection', 'Upgrade')
    handler.send_header('Sec-WebSocket-Accept', base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode())
    handler.end_headers()
    handler.close_connection = True
    handler.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # send each keystroke's echo right away
    return True


def _bridge(handler, argv, kick=b'', on_input=None):
    """Run argv on a pseudo-terminal and pipe it to the WebSocket until either side closes.
    Client frames: '0' + keystrokes, or '1' + {"cols":..,"rows":..}. Server frames: raw terminal output.
    kick: bytes typed into the terminal once it's up (Ctrl-L to redraw a re-attached shell's prompt)."""
    pid, fd = pty.fork()
    if pid == 0:  # child: only exec, nothing that could deadlock after fork in a threaded server
        try:
            os.execvp(argv[0], argv)
        finally:
            os._exit(127)
    lock = threading.Lock()

    def send(opcode, data=b''):
        with lock:
            handler.wfile.write(_frame(opcode, data))

    def pump():  # terminal -> browser
        try:
            while True:
                data = os.read(fd, 65536)
                if not data:
                    break
                send(0x2, data)
        except OSError:
            pass
        try:
            send(0x8)
        except OSError:
            pass

    threading.Thread(target=pump, daemon=True).start()
    if kick:
        def type_kick():
            try:
                os.write(fd, kick)
            except OSError:  # the terminal already closed
                pass
        threading.Timer(0.3, type_kick).start()
    try:
        while True:  # browser -> terminal
            op, data = _read_frame(handler.rfile)
            if op is None or op == 0x8:
                break
            if op == 0x9:
                send(0xA, data)
            elif op in (0x1, 0x2) and data:
                if data[:1] == b'0':
                    os.write(fd, data[1:])
                    if on_input:
                        on_input()
                elif data[:1] == b'1':
                    size = json.loads(data[1:])
                    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', int(size['rows']), int(size['cols']), 0, 0))
    except (OSError, ValueError):
        pass
    finally:
        for sig in (signal.SIGHUP, signal.SIGKILL):
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                break
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        os.close(fd)


# ---- entry point from the HTTP handler ----

def _fail(handler, msg):
    handler.wfile.write(_frame(0x2, f'\r\n\x1b[31m{msg}\x1b[0m\r\n'.encode()) + _frame(0x8))


def serve(handler, query, user):
    """GET /api/term?kind=project&dir=...[&aws=1] or ?kind=sandbox&uuid=..."""
    kind = query.get('kind', [''])[0]
    uuid = query.get('uuid', [''])[0]
    if kind not in ('project', 'sandbox') or (kind == 'sandbox' and not os.path.exists(os.path.join(workspace.SHELL_DIR, f'{uuid}.json'))):
        return handler.send_error(404)
    if not _handshake(handler):
        return
    try:
        if kind == 'project':
            box = workspace.workspace(user)
            if query.get('aws', [''])[0]:
                box.start_aws()
            argv, kick = workspace.terminal_argv(box, workspace.user_path(query.get('dir', [''])[0])), b''
        else:
            box = workspace.sandbox(user, uuid)
            # The shell printed its prompt before we attached: Ctrl-L asks it to redraw.
            argv, kick = ['docker', 'attach', box.name], b'\x0c'
    except workspace.Busy as e:
        return _fail(handler, str(e))
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as e:
        return _fail(handler, f'Could not start your workspace: {e}')
    _bridge(handler, argv, kick, on_input=box.touch)
