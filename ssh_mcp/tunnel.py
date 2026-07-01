"""SSH local port-forward tunnel support."""

from __future__ import annotations

import threading


class Tunnel:
    """SSH 本地端口转发隧道（-L local_port:remote_host:remote_port）。

    在本地监听 local_port，每个进入的连接通过 paramiko 的 direct-tcpip
    通道转发到远程 remote_host:remote_port。转发在独立线程中完成，不阻塞
    MCP 主事件循环。
    """

    def __init__(self, local_port: int, remote_host: str, remote_port: int, session_id: str):
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.session_id = session_id
        self._transport = None
        self._server_socket = None
        self._stop = threading.Event()
        self._accept_thread: threading.Thread | None = None
        self._client_threads: list[threading.Thread] = []

    def start(self, transport) -> None:
        import socket

        self._transport = transport
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(("127.0.0.1", self.local_port))
        self._server_socket.listen(5)
        self._server_socket.settimeout(0.5)
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def _accept_loop(self):

        while not self._stop.is_set():
            try:
                client_sock, _ = self._server_socket.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            t = threading.Thread(target=self._handle_connection, args=(client_sock,), daemon=True)
            self._client_threads.append(t)
            t.start()

    def _handle_connection(self, client_sock):

        chan = None
        try:
            chan = self._transport.open_channel(
                "direct-tcpip",
                (self.remote_host, self.remote_port),
                ("127.0.0.1", self.local_port),
            )
            if chan is None:
                return
            self._forward(client_sock, chan)
        except Exception:
            pass
        finally:
            for s in (client_sock, chan):
                if s is None:
                    continue
                try:
                    s.close()
                except Exception:
                    pass

    def _forward(self, sock, chan):
        """双向转发，直到任一端关闭。"""
        import socket

        def pipe(src, dst):
            try:
                while not self._stop.is_set():
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    dst.shutdown(socket.SHUT_WR)
                except Exception:
                    pass

        t1 = threading.Thread(target=pipe, args=(sock, chan), daemon=True)
        t2 = threading.Thread(target=pipe, args=(chan, sock), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def stop(self) -> None:
        self._stop.set()
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass

    def info(self) -> dict:
        return {
            "local_port": self.local_port,
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
            "session_id": self.session_id,
        }
