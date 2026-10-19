"""Container/public entry point; local development still uses the app factory directly."""

import os

import uvicorn


def configure_platform_environment():
    # Render supplies this trusted runtime variable after assigning the service URL.
    hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
    if hostname:
        os.environ.setdefault("ALLOWED_HOSTS", f"{hostname},127.0.0.1,localhost")
        os.environ.setdefault("CORS_ORIGINS", f"https://{hostname}")


def validate_public_environment():
    if os.getenv("DEPLOYMENT_MODE") != "public":
        return
    token = os.getenv("MANAGEMENT_TOKEN", "")
    if len(token) < 32:
        raise ValueError("公开部署需要设置至少 32 字符的 MANAGEMENT_TOKEN")
    hosts = [value.strip() for value in os.getenv("ALLOWED_HOSTS", "").split(",") if value.strip()]
    if not hosts or "*" in hosts:
        raise ValueError("公开部署需要明确配置 ALLOWED_HOSTS，不能使用 *")


def main():
    from pipeline.settings import Settings

    configure_platform_environment()
    validate_public_environment()
    port = int(os.getenv("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT 必须在 1 到 65535 之间")
    if os.getenv("BOOTSTRAP_REFERENCE") == "1":
        from eval.corpus import bootstrap
        from eval.run import evaluate
        from pipeline.store import Store

        store = Store(Settings())
        # Never overwrite an already populated production database with reference summaries.
        if store.coverage()["total_documents"] == 0:
            bootstrap(store)
            evaluate(store)
    uvicorn.run(
        "serve.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=port,
        workers=1,
        proxy_headers=False,
    )


if __name__ == "__main__":
    main()
