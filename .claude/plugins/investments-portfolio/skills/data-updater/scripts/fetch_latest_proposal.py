#!/usr/bin/env python3
"""미래에셋증권 게시판에서 최신 퇴직연금 상품제안서(DCIRP) xlsx 자동 다운로드.

게시판(categoryId=1494)의 모든 DCIRP xlsx 첨부를 수집해 파일명에 인코딩된
YY년MM월 을 파싱, 가장 최신 항목을 내려받는다 (DOM 순서/공지 고정 영향 없음).
게시판이 제공하는 파일명이 resource/ 명명 규칙과 동일하므로 그대로 사용한다.

표준 라이브러리만 사용. --convert 지정 시 같은 디렉터리의 xlsx_to_csv.py 로
CSV 까지 생성한다 (이 단계는 openpyxl 필요).

Usage:
    python fetch_latest_proposal.py --out-dir resource
    python fetch_latest_proposal.py --out-dir resource --convert
"""
import argparse
import re
import sys
import urllib.request
from pathlib import Path

LIST_URL = "https://securities.miraeasset.com/bbs/board/message/list.do?categoryId={cid}"
FILE_URL = "https://securities.miraeasset.com/bbs/board/message/file.do?attachmentId={aid}"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# <a href="file.do?attachmentId=2145056">26년06월_..._(DCIRP).xlsx(5.47M)</a>
_ENTRY = re.compile(rb'attachmentId=(\d+)"[^>]*>([^<]*\(DCIRP\)\.xlsx)\(', re.S)
_YYMM = re.compile(r"(\d{2})년(\d{2})월")


def _get(url, referer=None):
    headers = {"User-Agent": UA, "Accept-Encoding": "identity"}
    if referer:
        headers["Referer"] = referer
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=60
    ).read()


def find_latest(category_id):
    list_url = LIST_URL.format(cid=category_id)
    html = _get(list_url)
    best = None
    for aid, fname_bytes in _ENTRY.findall(html):
        fname = fname_bytes.decode("euc-kr")
        m = _YYMM.match(fname)
        if not m:
            continue
        key = (2000 + int(m.group(1)), int(m.group(2)))
        if best is None or key > best[0]:
            best = (key, aid.decode(), fname)
    if best is None:
        raise SystemExit("No DCIRP xlsx attachment found on the board page.")
    return best[1], best[2], list_url


def download(category_id, out_dir):
    aid, fname, list_url = find_latest(category_id)
    out_path = Path(out_dir) / fname
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = _get(FILE_URL.format(aid=aid), referer=list_url)
    if data[:2] != b"PK":
        raise SystemExit(f"Downloaded data is not an xlsx (got {len(data)} bytes).")
    out_path.write_bytes(data)
    print(f"Downloaded attachmentId={aid} -> {out_path} ({len(data):,} bytes)")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Download latest 퇴직연금 상품제안서 DCIRP xlsx")
    ap.add_argument("--category", default="1494", help="게시판 categoryId (기본 1494)")
    ap.add_argument("--out-dir", default="resource", help="저장 디렉터리 (기본 resource)")
    ap.add_argument("--convert", action="store_true", help="다운로드 후 xlsx_to_csv.py 로 CSV 생성")
    args = ap.parse_args()

    xlsx_path = download(args.category, args.out_dir)

    if args.convert:
        import importlib.util

        conv = Path(__file__).parent / "xlsx_to_csv.py"
        spec = importlib.util.spec_from_file_location("xlsx_to_csv", conv)
        if spec is None or spec.loader is None:
            print(f"Error: cannot load {conv}", file=sys.stderr)
            sys.exit(1)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        csv_path = xlsx_path.with_suffix(".csv")
        n = mod.convert(str(xlsx_path), str(csv_path))
        print(f"Converted {n} rows -> {csv_path}")

    from _consistency_gate import run_consistency_gate

    run_consistency_gate()


if __name__ == "__main__":
    main()
