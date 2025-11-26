#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fetch Coupang product 'btf' (below-the-fold) payloads.

Examples
(single)
    python btf.py \
        --product_id 487322 \
        --item_id 41045 \
        --vendor_item_id 3000014845 \
        --outdir /Users/ansunggeun/workspace/DS_project/data/outputs_btf \
        --cookie_file cookie.txt \
        --retries 2

(batch)
    # CSV columns (header): productId,itemId,vendorItemId
    python crawling/btf.py \
        --input products.csv \
        --cookie_file cookie.txt \
        --outdir /Users/ansunggeun/workspace/DS_project/data/outputs_btf \
        --jsonl /Users/ansunggeun/workspace/DS_project/data/outputs_btf/all_btf.jsonl

"""

import argparse
import csv
import json
import random
import time
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import requests
from urllib3.util.retry import Retry
import logging
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

# ── 기본값 ────────────────────────────────────────────
URL = "https://www.coupang.com/next-api/products/btf"
# 제공된 헤더 정보를 기반으로 최신 크롬 UA로 업데이트
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"

# ── 유틸 ─────────────────────────────────────────────
def load_cookie(cookie_file: Optional[str]) -> Optional[str]:
    if not cookie_file:
        return None
    p = Path(cookie_file)
    if not p.is_file():
        raise FileNotFoundError(f"cookie file not found: {cookie_file}")
    return p.read_text(encoding="utf-8").strip()

def build_referer(product_id: str,
                    item_id: Optional[str] = None,
                    vendor_item_id: Optional[str] = None) -> str:
    # item_id, vendor_item_id는 next-api 요청에는 필수가 아니지만, 
    # referer를 최대한 상세하게 구성하여 실제 브라우저 요청처럼 보이게 유지
    base = f"https://www.coupang.com/vp/products/{product_id}"
    return f"{base}?itemId={item_id}&vendorItemId={vendor_item_id}" if (item_id and vendor_item_id) else base

def build_headers(product_detail_url: str, cookie: Optional[str]) -> Dict[str, str]:
    """
    제공된 헤더 정보를 기반으로 수정된 함수.
    """
    h = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,ru;q=0.6,zh-CN;q=0.5,zh;q=0.4,ja;q=0.3,es;q=0.2",
        "accept-encoding": "gzip, deflate, br, zstd", # 요청하신 인코딩 추가
        "user-agent": UA,
        "origin": "https://www.coupang.com",
        "referer": product_detail_url,
        "priority": "u=1, i", # 요청하신 priority 추가
        "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"', # 요청하신 UA/Platform 힌트
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "macOS",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        # "x-requested-with": "XMLHttpRequest", # 최신 브라우저 요청에서 종종 생략됨. 안정성을 위해 삭제.
    }
    if cookie:
        h["cookie"] = cookie
    return h

def build_params(product_id: str,
                   item_id: Optional[str] = None,
                   vendor_item_id: Optional[str] = None) -> Dict[str, str]:
    # btf는 page 개념이 없음
    params = {"productId": str(product_id)}
    if vendor_item_id:
        params["vendorItemId"] = str(vendor_item_id)
    if item_id:
        params["itemId"] = str(item_id)
    return params

def save_json(obj, outdir: Path, filename: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / filename
    out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path

# ── 네트워킹 ─────────────────────────────────────────
def make_session(retries: int = 2) -> requests.Session:
    s = requests.Session()
    # 재시도 설정 강화: 429뿐만 아니라 5xx 에러에도 대비
    retry = Retry(
        total=retries, connect=retries, read=retries, status=retries,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def safe_request(url: str, headers: Dict[str, str], params: Dict[str, str], retries: int = 2) -> requests.Response:
    """짧은 타임아웃 + 지수 백오프. session 재시도로 1차 방어, 여기서 추가 백오프."""
    sess = make_session(retries=retries)
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            # 5초 연결 타임아웃, 10초 읽기 타임아웃
            resp = sess.get(url, headers=headers, params=params, timeout=(5, 10))
            # Session Retry가 Status Code를 처리하지만, 여기서도 명시적으로 체크
            if resp.status_code >= 400 and resp.status_code not in [429, 500, 502, 503, 504]:
                # Retry 대상이 아닌 에러는 즉시 리턴하거나 예외 발생
                resp.raise_for_status() 
            return resp
        except requests.exceptions.RequestException as e:
            last_err = e
            if isinstance(e, requests.Timeout):
                delay = (2 ** attempt) * 0.8 + random.uniform(0, 0.6)
                print(f"[retry {attempt+1}/{retries}] timeout → wait {delay:.2f}s")
                time.sleep(delay)
            elif attempt < retries:
                logger.warning("[retry %d/%d] error: %s", attempt + 1, retries, e)
                time.sleep(1.0) # 일반 RequestException의 경우 1초 대기 후 재시도
            else:
                pass # 마지막 시도는 그냥 예외 발생
    
    # 마지막 재시도까지 실패한 경우
    if last_err:
        raise last_err 
    raise RuntimeError("request failed after all retries")

# ── 단일 호출 ────────────────────────────────────────
def fetch_btf(product_id: str,
              item_id: Optional[str] = None,
              vendor_item_id: Optional[str] = None,
              cookie: Optional[str] = None,
              outdir: Optional[str] = None,
              retries: int = 2):
    referer = build_referer(product_id, item_id, vendor_item_id)
    headers = build_headers(referer, cookie)
    params = build_params(product_id, item_id=item_id, vendor_item_id=vendor_item_id)

    logger.debug("[REQUEST] %s referer=%s params=%s", URL, referer, params)

    resp = safe_request(URL, headers, params, retries=retries)
    logger.debug("status: %s url: %s", resp.status_code, resp.url)

    try:
        data = resp.json()
    except Exception:
        # JSON 디코딩 실패 시 원본 텍스트를 저장
        data = {"error": "JSON Decode Failed", "status_code": resp.status_code, "raw_text_start": resp.text[:200]}
        logger.warning("경고: 응답 본문이 JSON 형식이 아닙니다.")
        
    if outdir:
        ts = int(time.time() * 1000)
        # 파일명에 세 파라미터를 최대한 반영
        suffix = []
        if item_id: suffix.append(f"i{item_id}")
        if vendor_item_id: suffix.append(f"v{vendor_item_id}")
        base = f"btf_{product_id}" + (("_" + "_".join(suffix)) if suffix else "")
        p = save_json(data, Path(outdir), f"{base}_{ts}.json")
        logger.info("saved → %s", p)

    return resp, data
