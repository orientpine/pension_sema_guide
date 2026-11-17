"""공개 HTML 픽스처와 로컬 HTTP 재현 서버로 전송·선택 계약을 검사한다."""
import ssl
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

import fetch_latest_proposal as proposal


FIXTURES = Path(__file__).parent / "fixtures" / "fetch_proposal"


@pytest.fixture
def board_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """TLS만 로컬 평문으로 대체하고 urllib/HTTP 프레이밍은 실제로 실행한다."""
    full = (FIXTURES / "board.html").read_text(encoding="utf-8").encode("euc-kr")
    partial = (FIXTURES / "partial-board.html").read_text(encoding="utf-8").encode("euc-kr")

    class Board(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            # 실사이트의 close 응답은 중간 HTML이 누락된다. keep-alive의
            # chunked 응답에는 전체 첨부가 있다. HTTP 요청부터 재현한다.
            chunked = self.headers.get("Connection", "").lower() == "keep-alive"
            body = full if chunked else partial
            self.send_response(200)
            self.send_header("Content-Type", "text/html;charset=EUC-KR")
            if chunked:
                self.send_header("Transfer-Encoding", "chunked")
            else:
                self.send_header("Connection", "close")
            self.end_headers()
            if chunked:
                for start in range(0, len(body), 37):
                    chunk = body[start:start + 37]
                    self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                self.wfile.write(b"0\r\n\r\n")
            else:
                self.wfile.write(body)
            self.wfile.flush()

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Board)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", lambda self, sock, **kwargs: sock)
    url = f"https://127.0.0.1:{server.server_port}/list.do?categoryId={{cid}}"
    monkeypatch.setattr(proposal, "LIST_URL", url)
    try:
        yield url.format(cid="1494")
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


def test_latest_selection_survives_close_delimited_board(board_url: str):
    assert proposal.find_latest("1494") == (
        "2148292", "26년11월_상품제안서_퇴직연금(DCIRP).xlsx", board_url,
    )


def test_latest_selection_ignores_pin_order_db_and_pdf(monkeypatch: pytest.MonkeyPatch):
    body = (FIXTURES / "board.html").read_text(encoding="utf-8").encode("euc-kr")
    monkeypatch.setattr(proposal, "_get", lambda url: body)

    assert proposal.find_latest("1494")[:2] == (
        "2148292", "26년11월_상품제안서_퇴직연금(DCIRP).xlsx",
    )


def test_board_without_dcirp_xlsx_is_rejected(monkeypatch: pytest.MonkeyPatch):
    body = (FIXTURES / "partial-board.html").read_text(encoding="utf-8").encode("euc-kr")
    monkeypatch.setattr(proposal, "_get", lambda url: body)

    with pytest.raises(SystemExit):
        proposal.find_latest("1494")
