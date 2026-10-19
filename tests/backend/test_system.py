import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from eval.corpus import bootstrap
from eval.run import evaluate, faithfulness
from pipeline.collectors import Fetcher, article, collect_source, price_records
from pipeline.models import Record, utcnow
from pipeline.runner import import_jsonl
from pipeline.settings import Settings
from pipeline.store import Store
from serve.app import create_app
from serve.retrieval import infer_filters, query


def test_module_import_does_not_create_database(tmp_path):
    target = tmp_path / "must-not-be-created"
    result = subprocess.run(
        [sys.executable, "-c", "import serve.app; import eval.run; import pipeline.__main__"],
        env={**os.environ, "DATA_DIR": str(target)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert not target.exists()


@pytest.mark.parametrize(
    "values",
    [
        {"request_timeout": 0},
        {"request_timeout": float("nan")},
        {"request_interval": -1},
        {"http_retries": -1},
        {"http_retries": 6},
    ],
)
def test_invalid_settings_fail_before_creating_data(tmp_path, values):
    target = tmp_path / "invalid-config"
    with pytest.raises(ValueError):
        Settings(data_dir=target, **values)
    assert not target.exists()


def test_concurrent_evaluations_write_complete_atomic_reports(store):
    bootstrap(store)
    with ThreadPoolExecutor(max_workers=3) as executor:
        reports = list(executor.map(lambda _: evaluate(store), range(3)))
    path = store.settings.data_dir / "eval" / "latest.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["created_at"] in {report["created_at"] for report in reports}
    assert len(saved["results"]) == 20
    assert list(path.parent.glob("*.tmp")) == []


@pytest.fixture
def store(tmp_path):
    return Store(Settings(data_dir=tmp_path, request_interval=0, http_retries=1))


def document(**changes):
    values = dict(
        kind="policy",
        source="TEST fixture",
        url="https://example.org/policy",
        title="澳大利亚锂出口政策测试",
        text="这是一条隔离测试数据：澳大利亚锂出口政策要求出口商提交申报材料，不作为真实政策使用。",
        published_at=utcnow() - timedelta(days=2),
        countries=["AU"],
        minerals=["锂"],
    )
    values.update(changes)
    return Record(**values)


def test_canonical_dedup_and_metadata_update(store):
    first = store.upsert(document(url="https://example.org/policy/?utm_source=x#top"))
    assert (
        store.upsert(
            document(
                url="https://example.org/policy",
                published_at=store.get(first["id"])["published_at"],
            )
        )["status"]
        == "unchanged"
    )
    assert store.upsert(document(url="https://example.org/copy"))["status"] == "duplicate"
    updated = store.upsert(document(title="更正后的澳洲锂出口政策标题", is_reference=True))
    assert updated["status"] == "updated"
    assert store.coverage()["counts"]["policy"] == 0
    assert store.coverage()["reference_documents"] == 1


def test_replacement_removes_stale_vectors(store):
    original = document(text=("隔离测试：澳大利亚锂出口管理资料，须准备申报材料。" * 100))
    key = store.upsert(original)["id"]
    assert store.coverage()["chunks"] > 1
    store.upsert(
        original.model_copy(update={"text": "隔离测试修订后仅保留这段澳大利亚锂出口政策原文信息。"})
    )
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM vectors").fetchone()[0] == 1
        assert (
            db.execute("SELECT count(*) FROM chunks WHERE document_id=?", (key,)).fetchone()[0] == 1
        )
    assert Store(store.settings).get(key)["text"].startswith("隔离测试修订")


def test_recent_count_excludes_old_reference_and_chunk_inflation(store):
    store.upsert(document(text="澳大利亚锂政策测试资料，明确标识为隔离数据。" * 120))
    store.upsert(
        document(
            url="https://example.org/old",
            text="旧的澳大利亚锂政策，仅用于日期过滤的测试数据。",
            published_at=utcnow() - timedelta(days=40),
        )
    )
    store.upsert(
        document(
            url="https://example.org/ref",
            text="历史参考摘要的隔离测试资料，不能作为近期采集量。",
            is_reference=True,
        )
    )
    coverage = store.coverage()
    assert coverage["counts"]["policy"] == 1
    assert coverage["chunks"] > coverage["total_recent"]
    assert coverage["passed"] is False


def test_query_filters_citations_and_abstention(store):
    key = store.upsert(document())["id"]
    store.upsert(
        document(
            url="https://example.org/china",
            title="中国锂矿测试政策",
            text="隔离测试：中国锂矿政策要求登记申报，应仅在中国过滤条件下出现。",
            countries=["CN"],
        )
    )
    answer = query(store, "近 7 天澳洲锂出口政策有何变化？")
    assert [source["id"] for source in answer["sources"]] == [key]
    assert answer["filters"]["countries"] == ["AU"]
    assert answer["sources"][0]["url"] == "https://example.org/policy"
    assert faithfulness(answer) == 1
    assert query(store, "近 1 天澳洲锂出口政策有何变化？")["abstained"]
    assert query(store, "中国铜政策有何变化？")["abstained"]


def test_calendar_and_explicit_filter():
    filters = infer_filters("本月澳洲锂政策", {"countries": ["CN"]}, "2026-10-18T12:00:00+08:00")
    assert filters["countries"] == ["CN"]
    assert filters["since"].startswith("2026-10-01T00:00:00")
    assert infer_filters("近七天政策", as_of="2026-10-18")["since"].startswith("2026-10-11")


def test_price_decimal_identity_and_validation(store):
    content = "published_at,market,instrument,contract,quote_type,currency,unit,price\n2026-01-01T16:00:00+08:00,LME,copper,3M,settlement,USD,tonne,1234.123456\n"
    record = list(price_records(content, "LME", "https://example.org/prices"))[0]
    assert record.price == Decimal("1234.123456")
    key = store.upsert(record)["id"]
    corrected = record.model_copy(
        update={"price": Decimal("1234.22"), "text": record.text.replace("1234.123456", "1234.22")}
    )
    assert store.upsert(corrected)["status"] == "updated"
    assert store.get(key)["price"] == "1234.22"
    with pytest.raises(ValidationError, match="GFEX"):
        Record(
            **{
                **record.model_dump(),
                "market": "SHFE",
                "instrument": "lithium",
                "minerals": [],
                "title": "lithium测试",
                "text": "这是一条碳酸锂行情测试记录，禁止错误标注交易所。",
            }
        )
    with pytest.raises(ValueError, match="时区"):
        list(price_records(content.replace("+08:00", ""), "LME", "https://example.org/prices"))
    with pytest.raises(ValidationError):
        document(published_at=utcnow() + timedelta(days=1))


def test_article_extract_publication_and_cleaning():
    html = (
        '<html><head><meta property="article:published_time" content="2026-01-02T08:00:00Z"></head><body><h1>Copper mining news</h1><article><nav>menu</nav>'
        + "Actual copper mine production report. " * 12
        + "<script>secret()</script></article></body></html>"
    )
    record = article(html, "https://example.org/a", "Test", "news")
    assert record.published_at.day == 2
    assert "secret" not in record.text and "menu" not in record.text
    with pytest.raises(ValueError, match="发布日期"):
        article(
            "<h1>title</h1><article>" + "body " * 100 + "</article>",
            "https://example.org/b",
            "Test",
            "news",
        )
    with pytest.raises(ValueError, match="正文不足"):
        article(
            "<h1>title</h1><article>Login now</article>",
            "https://example.org/b",
            "Test",
            "news",
            record.published_at,
        )


def test_http_retry_robots_and_raw_snapshot(store):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if calls.count("/feed") == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, text="actual raw bytes")

    fetcher = Fetcher(store.settings)
    fetcher.client.close()
    fetcher.client = httpx.Client(transport=httpx.MockTransport(handler))
    response, raw = fetcher.get("https://example.org/feed")
    assert response.text == "actual raw bytes"
    assert (store.settings.data_dir / raw).read_text() == "actual raw bytes"
    assert calls == ["/robots.txt", "/feed", "/feed"]
    fetcher.close()


def test_robots_disallow_is_respected(store):
    fetcher = Fetcher(store.settings)
    fetcher.client.close()
    fetcher.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="User-agent: *\nDisallow: /private")
        )
    )
    with pytest.raises(PermissionError):
        fetcher.get("https://example.org/private")
    fetcher.close()


def test_collector_rss_to_fulltext_and_missing_configuration(store, monkeypatch):
    from pipeline.collectors import SOURCE_SPECS

    date = (utcnow() - timedelta(days=2)).isoformat()
    xml = f'<rss version="2.0"><channel><title>Test RSS</title><item><title>Copper</title><link>https://example.org/story</link><pubDate>{date}</pubDate></item></channel></rss>'
    html = (
        f'<h1>Copper test story</h1><meta property="article:published_time" content="{date}"><article>'
        + "Copper production from a test-only source. " * 12
        + "</article>"
    )

    def get(self, url, **kwargs):
        return httpx.Response(
            200,
            text=xml if "/feed" in url else html,
            headers={"content-type": "application/rss+xml" if "/feed" in url else "text/html"},
            request=httpx.Request("GET", url),
        ), ""

    monkeypatch.setenv("MINING_RSS_URLS", "https://example.org/feed/")
    monkeypatch.setattr(Fetcher, "get", get)
    report = collect_source(store, SOURCE_SPECS[0], limit=1, max_pages=3)
    assert report["inserted"] == 1
    assert report["status"] == "completed"
    assert store.coverage()["counts"]["news"] == 1
    monkeypatch.setenv("SPGLOBAL_RSS_URLS", "")
    assert collect_source(store, SOURCE_SPECS[1])["status"] == "needs_configuration"


def test_citation_support_does_not_reward_unfounded_claims():
    assert (
        faithfulness(
            {
                "abstained": False,
                "sources": [{"id": "1", "excerpt": "可靠原文"}],
                "claims": [{"source_id": "1", "text": "凭空编造"}],
            }
        )
        == 0
    )
    assert faithfulness({"abstained": True}) is None


def test_malformed_import_does_not_partially_ingest(store, tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text(document().model_dump_json() + "\n{}", encoding="utf-8")
    with pytest.raises(ValidationError):
        import_jsonl(store, path)
    assert store.coverage()["total_documents"] == 0


def test_reference_eval_is_reproducible_and_local_only(store):
    assert bootstrap(store)["inserted"] == 10
    assert bootstrap(store)["unchanged"] == 10
    report = evaluate(store)
    assert report["questions"] == 20
    assert report["recall_at_5"] >= 0.8
    assert report["answer_faithfulness"] == 1
    assert store.coverage()["total_recent"] == 0
    assert (
        json.loads((store.settings.data_dir / "eval/latest.json").read_text(encoding="utf-8"))[
            "benchmark_hash"
        ]
        == report["benchmark_hash"]
    )


def test_api_validation_filters_and_management(store, monkeypatch):
    bootstrap(store)
    monkeypatch.setenv("MANAGEMENT_TOKEN", "test-token")
    client = TestClient(create_app(store.settings))
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.post(
        "/query", json={"question": "澳大利亚关键矿产战略对本国加工能力有何目标？"}
    ).json()["sources"]
    assert client.post("/api/query", json={"question": " "}).status_code == 422
    assert client.post("/api/query", json={"question": "政策", "top_k": 50}).status_code == 422
    assert (
        client.post(
            "/api/query",
            json={"question": "政策", "filters": {"since": "2026-10-18", "until": "2026-10-01"}},
        ).status_code
        == 422
    )
    assert client.get("/api/documents?limit=1001").status_code == 422
    assert client.get("/api/documents/no-such-id").status_code == 404
    assert client.get("/api/overview").json()["coverage"]["passed"] is False
    assert client.post("/api/eval").status_code == 401
    assert (
        client.post("/api/eval", headers={"Authorization": "Bearer test-token"}).json()["questions"]
        == 20
    )
    assert client.get("/api/eval").json()["questions"] == 20
