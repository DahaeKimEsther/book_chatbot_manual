"""카카오 책 검색 도구 테스트 (실제 API 호출, 목킹 없음)"""
import pytest
import requests

from book_chatbot.tool import kakao_book_search
from book_chatbot.utils import kakao_book_api

EXPECTED_KEYS = {"title", "authors", "publisher", "isbn", "datetime", "price", "sale_price", "contents", "url", "status"}


def test_kakao_book_search_basic():
    """기본 검색: 결과가 있고 필요한 필드가 포함되어야 한다"""
    result = kakao_book_search.invoke({"query": "미움받을 용기"})
    assert len(result) > 0
    assert set(result[0].keys()) <= EXPECTED_KEYS
    assert "title" in result[0] and "isbn" in result[0]


def test_kakao_book_search_target_title_and_size():
    """target=title, size 지정이 반영되어야 한다"""
    result = kakao_book_search.invoke({"query": "미움받을 용기", "target": "title", "size": 3})
    assert 1 <= len(result) <= 3
    assert any("미움받을 용기" in doc["title"] for doc in result)


def test_kakao_book_search_isbn():
    """ISBN 검색: 첫 결과의 ISBN으로 다시 검색하면 같은 책이 나와야 한다"""
    first = kakao_book_search.invoke({"query": "미움받을 용기", "target": "title", "size": 1})[0]
    isbn13 = first["isbn"].split()[-1]
    result = kakao_book_search.invoke({"query": isbn13, "target": "isbn"})
    assert len(result) > 0
    assert isbn13 in result[0]["isbn"]


def test_kakao_book_api_invalid_key(monkeypatch):
    """잘못된 키는 HTTP 에러로 드러나야 한다 (조용히 실패하지 않음)"""
    monkeypatch.setenv("KAKAO_REST_API_KEY", "invalid-key")
    with pytest.raises(requests.HTTPError):
        kakao_book_api({"query": "테스트"})
