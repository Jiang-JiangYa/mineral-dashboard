import os

import pytest

from pipeline.models import Record, utcnow
from pipeline.settings import Settings
from pipeline.store import Store
from pipeline.text import clean_text
from serve.__main__ import configure_platform_environment, main, validate_public_environment


def test_public_entrypoint_requires_explicit_admin_token_and_hosts(monkeypatch):
    monkeypatch.setenv("DEPLOYMENT_MODE", "public")
    monkeypatch.delenv("MANAGEMENT_TOKEN", raising=False)
    with pytest.raises(ValueError, match="MANAGEMENT_TOKEN"):
        validate_public_environment()
    monkeypatch.setenv("MANAGEMENT_TOKEN", "test-only-token-" * 3)
    monkeypatch.setenv("ALLOWED_HOSTS", "*")
    with pytest.raises(ValueError, match="ALLOWED_HOSTS"):
        validate_public_environment()
    monkeypatch.setenv("ALLOWED_HOSTS", "example.org,127.0.0.1")
    validate_public_environment()


def test_render_domain_defaults_do_not_override_custom_domains(monkeypatch):
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "test-service.onrender.com")
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    configure_platform_environment()
    assert os.environ["ALLOWED_HOSTS"] == "test-service.onrender.com,127.0.0.1,localhost"
    assert os.environ["CORS_ORIGINS"] == "https://test-service.onrender.com"
    monkeypatch.setenv("ALLOWED_HOSTS", "my-domain.example.org")
    configure_platform_environment()
    assert os.environ["ALLOWED_HOSTS"] == "my-domain.example.org"


def test_first_boot_initializes_reference_but_never_overwrites_existing_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DEPLOYMENT_MODE", "test")
    monkeypatch.setenv("BOOTSTRAP_REFERENCE", "1")
    monkeypatch.setenv("PORT", "18001")
    started = []
    monkeypatch.setattr(
        "serve.__main__.uvicorn.run", lambda *args, **kwargs: started.append(kwargs)
    )
    main()
    store = Store(Settings(data_dir=tmp_path))
    assert store.coverage()["reference_documents"] == 10
    target = store.documents("policy", limit=1)["items"][0]
    target["text"] = "这是用于隔离测试的已有数据库修订内容，不应被启动初始化覆盖。"
    target["published_at"] = utcnow()
    store.upsert(Record.model_validate(target))
    main()
    assert store.get(target["id"])["text"] == clean_text(target["text"])
    assert all(call["port"] == 18001 and call["workers"] == 1 for call in started)
