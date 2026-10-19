import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import timedelta

import sqlite_vec

from .embedding import Encoder
from .models import COUNTRIES, MINERALS, Record, identify, utcnow
from .text import canonical_url, chunks, clean_text, digest, record_id


class Store:
    def __init__(self, settings):
        self.settings = settings
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = settings.data_dir / "mineral.sqlite3"
        self.encoder = Encoder(settings)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS documents(
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, source TEXT NOT NULL,
                    url TEXT NOT NULL, title TEXT NOT NULL, text TEXT NOT NULL,
                    published_at TEXT NOT NULL, fetched_at TEXT NOT NULL,
                    content_hash TEXT NOT NULL, is_reference INTEGER NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS documents_date ON documents(published_at,kind);
                CREATE INDEX IF NOT EXISTS documents_hash ON documents(content_hash,kind);
                CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE, position INTEGER, text TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(document_id);
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT, report TEXT NOT NULL);
            """)
            current = db.execute("SELECT value FROM meta WHERE key='encoder'").fetchone()
            if current and current[0] != self.encoder.signature:
                raise RuntimeError(
                    "向量模型发生变化：请使用新的 DATA_DIR 并重新入库，禁止混用不同编码器"
                )
            db.execute("INSERT OR IGNORE INTO meta VALUES('encoder',?)", (self.encoder.signature,))
            db.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS vectors USING vec0(id TEXT PRIMARY KEY, embedding float[{self.encoder.dimension}])"
            )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def upsert(self, record: Record):
        record = record.model_copy(deep=True)
        record.text, record.title = clean_text(record.text), clean_text(record.title)
        if len(record.text) < 20:
            raise ValueError("清洗后正文过短")
        record.url = canonical_url(record.url)
        record.minerals = sorted(
            set(record.minerals or identify(record.title + " " + record.text, MINERALS))
        )
        record.countries = sorted(
            set(record.countries or identify(record.title + " " + record.text, COUNTRIES))
        )
        key = record_id(record)
        content_hash = digest(record.text)
        passage_list = chunks(record.text)
        vectors = [
            (digest(f"{key}:{i}"), self.encoder.blob(record.title + "\n" + text))
            for i, text in enumerate(passage_list)
        ]
        with self.lock, self.connect() as db:
            previous = db.execute(
                "SELECT content_hash,payload FROM documents WHERE id=?", (key,)
            ).fetchone()
            old_payload = json.loads(previous["payload"]) if previous else {}
            new_payload = record.model_dump(mode="json")
            old_payload.pop("fetched_at", None)
            new_payload.pop("fetched_at", None)
            if previous and old_payload == new_payload:
                return {"id": key, "status": "unchanged"}
            # Price rows have their own observation key, not document-body deduplication.
            if record.kind != "price":
                duplicate = db.execute(
                    "SELECT id FROM documents WHERE content_hash=? AND kind=? AND id<>?",
                    (content_hash, record.kind, key),
                ).fetchone()
                if duplicate:
                    return {"id": duplicate[0], "status": "duplicate"}
            for row in db.execute("SELECT id FROM chunks WHERE document_id=?", (key,)).fetchall():
                db.execute("DELETE FROM vectors WHERE id=?", (row[0],))
            db.execute("DELETE FROM chunks WHERE document_id=?", (key,))
            db.execute(
                """INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,source=excluded.source,url=excluded.url,title=excluded.title,
                text=excluded.text,published_at=excluded.published_at,fetched_at=excluded.fetched_at,
                content_hash=excluded.content_hash,is_reference=excluded.is_reference,payload=excluded.payload""",
                (
                    key,
                    record.kind,
                    record.source,
                    record.url,
                    record.title,
                    record.text,
                    record.published_at.isoformat(),
                    record.fetched_at.isoformat(),
                    content_hash,
                    int(record.is_reference),
                    record.model_dump_json(),
                ),
            )
            for i, (chunk_id, vector) in enumerate(vectors):
                db.execute(
                    "INSERT INTO chunks VALUES(?,?,?,?)", (chunk_id, key, i, passage_list[i])
                )
                db.execute("INSERT INTO vectors(id,embedding) VALUES(?,?)", (chunk_id, vector))
        return {"id": key, "status": "updated" if previous else "inserted"}

    @staticmethod
    def public(row):
        record = json.loads(row["payload"])
        record.update(
            id=row["id"],
            date=record["published_at"][:10],
            mineral="、".join(record["minerals"]),
            category=record["kind"],
        )
        record.pop("raw_path", None)
        return record

    def documents(self, kind=None, limit=100, offset=0):
        where, args = ("WHERE kind=?", [kind]) if kind else ("", [])
        with self.connect() as db:
            total = db.execute(f"SELECT count(*) FROM documents {where}", args).fetchone()[0]
            rows = db.execute(
                f"SELECT * FROM documents {where} ORDER BY published_at DESC,id LIMIT ? OFFSET ?",
                [*args, limit, offset],
            ).fetchall()
        return {
            "items": [self.public(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (key,)).fetchone()
        return self.public(row) if row else None

    def coverage(self, days=30):
        start = (utcnow() - timedelta(days=days)).isoformat()
        with self.connect() as db:
            rows = db.execute(
                "SELECT kind,count(*) AS n FROM documents WHERE published_at>=? AND is_reference=0 GROUP BY kind",
                (start,),
            ).fetchall()
            counts = {kind: 0 for kind in ("news", "policy", "price")}
            counts.update({row["kind"]: row["n"] for row in rows})
            total = db.execute("SELECT count(*) FROM documents").fetchone()[0]
            reference = db.execute(
                "SELECT count(*) FROM documents WHERE is_reference=1"
            ).fetchone()[0]
            chunk_count = db.execute("SELECT count(*) FROM chunks").fetchone()[0]
        return {
            "days": days,
            "counts": counts,
            "total_recent": sum(counts.values()),
            "total_documents": total,
            "reference_documents": reference,
            "chunks": chunk_count,
            "target_per_kind": 200,
            "deficits": {kind: max(0, 200 - count) for kind, count in counts.items()},
            "passed": all(count >= 200 for count in counts.values()),
            "encoder": self.encoder.signature,
        }

    def save_run(self, run_id, started_at, status, report, finished_at=None):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO runs VALUES(?,?,?,?,?)",
                (run_id, started_at, finished_at, status, json.dumps(report, ensure_ascii=False)),
            )

    def runs(self, limit=10):
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row, report=json.loads(row["report"])) for row in rows]
