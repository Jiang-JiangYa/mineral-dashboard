import json
import uuid

from filelock import FileLock

from .collectors import SOURCE_SPECS, collect_source
from .models import Record, utcnow


def collect(store, sources=None, days=30, limit=200, max_pages=250):
    with FileLock(str(store.settings.data_dir / "pipeline.lock"), timeout=0):
        run_id, started = str(uuid.uuid4()), utcnow().isoformat()
        report = {"sources": []}
        store.save_run(run_id, started, "running", report)
        try:
            for spec in SOURCE_SPECS:
                if sources and spec[0] not in sources:
                    continue
                report["sources"].append(collect_source(store, spec, days, limit, max_pages))
                store.save_run(run_id, started, "running", report)
            report["coverage"] = store.coverage()
            status = "completed" if report["coverage"]["passed"] else "completed_with_gaps"
            store.save_run(run_id, started, status, report, utcnow().isoformat())
        except Exception:
            store.save_run(run_id, started, "failed", report, utcnow().isoformat())
            raise
        return dict(id=run_id, status=status, **report)


def import_jsonl(store, path):
    # Validate whole input first so a malformed line never creates a silently partial import.
    records = [
        Record.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    result = {}
    for record in records:
        status = store.upsert(record)["status"]
        result[status] = result.get(status, 0) + 1
    return result
