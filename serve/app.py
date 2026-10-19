import hmac
import json
import os
import threading
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pipeline.collectors import SOURCE_SPECS
from pipeline.runner import collect
from pipeline.settings import ROOT, Settings, csv_env
from pipeline.store import Store

from .retrieval import query
from .schemas import CollectionBody, QueryBody


def create_app(settings=None):
    settings = settings or Settings()
    store = Store(settings)
    job_lock = threading.Lock()
    job = {"status": "idle", "error": None}
    app = FastAPI(title="矿观三源情报 API", version="0.3.0")
    app.state.store = store
    app.add_middleware(
        CORSMiddleware,
        allow_origins=csv_env(
            "CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000"
        ),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=csv_env("ALLOWED_HOSTS", "127.0.0.1,localhost,testserver"),
    )

    def authorize(request, authorization):
        token = os.getenv("MANAGEMENT_TOKEN", "")
        if token:
            if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
                raise HTTPException(401, "采集/评估操作需要 MANAGEMENT_TOKEN")
        elif request.client.host not in ("127.0.0.1", "::1", "testclient"):
            raise HTTPException(403, "未设置管理令牌时只允许本机触发作业")
        origin = request.headers.get("origin")
        if origin and origin not in csv_env(
            "CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000"
        ):
            raise HTTPException(403, "不允许此网页来源触发管理操作")

    @app.get("/api/health")
    def health():
        return dict(status="ok", database="sqlite+sqlite-vec", encoder=store.encoder.signature)

    @app.post("/query")
    @app.post("/api/query")
    def ask(body: QueryBody):
        return query(
            store,
            body.question,
            body.top_k,
            body.filters.model_dump(mode="json") if body.filters else None,
            body.as_of.isoformat() if body.as_of else None,
        )

    @app.get("/api/documents")
    def documents(
        kind: Literal["news", "policy", "price"] | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        return store.documents(kind, limit, offset)

    @app.get("/api/documents/{key}")
    def document(key: str):
        record = store.get(key)
        if not record:
            raise HTTPException(404, "未找到文档")
        return record

    def evaluation():
        path = settings.data_dir / "eval" / "latest.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def source_status():
        latest = {}
        for run in reversed(store.runs(50)):
            for source in run["report"].get("sources", []):
                latest[source["id"]] = source
        return [
            dict(
                id=key,
                name=name,
                kind=kind,
                configured=bool(csv_env(env, default)),
                status=latest.get(key, {}).get(
                    "status", "not_run" if csv_env(env, default) else "needs_configuration"
                ),
                last_run=latest.get(key),
                configuration_key=env,
            )
            for key, name, kind, _, env, default in SOURCE_SPECS
        ]

    @app.get("/api/overview")
    def overview():
        return dict(
            coverage=store.coverage(),
            sources=source_status(),
            evaluation=evaluation(),
            job=job.copy(),
        )

    @app.get("/api/sources")
    def sources():
        return source_status()

    @app.get("/api/prices")
    def prices(limit: int = Query(1000, ge=1, le=1000)):
        return store.documents("price", limit)

    @app.get("/api/runs")
    def runs():
        return dict(items=store.runs(), job=job.copy())

    @app.get("/api/eval")
    def eval_report():
        return evaluation()

    @app.post("/api/collect", status_code=202)
    def trigger(
        body: CollectionBody, request: Request, authorization: str | None = Header(default=None)
    ):
        authorize(request, authorization)
        if not job_lock.acquire(blocking=False):
            raise HTTPException(409, "已有作业正在运行")
        job.update(status="running", error=None)

        def work():
            try:
                result = collect(store, body.sources, body.days, body.limit, body.max_pages)
                job.update(status=result["status"], run_id=result["id"])
            except Exception as exc:
                job.update(status="failed", error=str(exc))
            finally:
                job_lock.release()

        threading.Thread(target=work, daemon=True).start()
        return {
            "status": "accepted",
            "message": "请通过 /api/runs 查看进度；服务退出会中断当前作业",
        }

    @app.post("/api/eval")
    def run_eval(request: Request, authorization: str | None = Header(default=None)):
        authorize(request, authorization)
        from eval.run import evaluate

        return evaluate(store)

    assets = ROOT / "dist" / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        path = ROOT / "dist" / "index.html"
        if not path.exists():
            return {
                "message": "API 已运行；执行 npm run build 后重启服务即可在此打开网页",
                "docs": "/docs",
            }
        return FileResponse(path)

    return app
