"""Local retrieval of test-backed cases. No training or model weight mutation."""

import hashlib
import json
import re
import time


def redact(text):
    return re.sub(
        r"(?i)\b(api[_ -]?key|password|secret|token)\s*[:=]\s*[\"\']?[^\s,;\"\']+",
        r"\1=[REDACTED]",
        str(text),
    )


class CaseMemory:
    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS cases USING fts5(id UNINDEXED, request, summary, recipe UNINDEXED, evidence UNINDEXED, metadata UNINDEXED, created UNINDEXED)"
            )

    def remember(self, task, recipe, evidence, summary, model):
        request = redact(task["prompt"])[:2000]
        fingerprint = hashlib.sha256(
            json.dumps(
                [
                    request,
                    recipe,
                    [
                        (c["path"], hashlib.sha256(c["after"].encode()).hexdigest())
                        for c in task["changes"]
                    ],
                ],
                sort_keys=True,
            ).encode()
        ).hexdigest()
        metadata = {
            "task": task["id"],
            "source": "local-test-and-review",
            "model": model,
            "patches": [
                {
                    "path": c["path"],
                    "sha256": hashlib.sha256(c["after"].encode()).hexdigest(),
                }
                for c in task["changes"]
            ],
            "root_cause_status": "model hypothesis, not independently proven",
            "weight_training": False,
        }
        with self.store.connect() as db:
            if db.execute("SELECT 1 FROM cases WHERE id=?", (fingerprint,)).fetchone():
                return
            db.execute(
                "INSERT INTO cases VALUES(?,?,?,?,?,?,?)",
                (
                    fingerprint,
                    request,
                    redact(summary)[:1500],
                    recipe,
                    redact(evidence)[-4000:],
                    json.dumps(metadata),
                    str(time.time()),
                ),
            )

    def search(self, query="", limit=20):
        limit = max(1, min(int(limit), 100))
        with self.store.connect() as db:
            if query:
                words = list(dict.fromkeys(re.findall(r"[\w]{3,}", query.lower())))[:10]
                if not words:
                    return []
                expression = " OR ".join('"' + word + '"' for word in words)
                rows = db.execute(
                    "SELECT id,request,summary,recipe,evidence,metadata,created FROM cases WHERE cases MATCH ? AND CAST(created AS REAL)>? ORDER BY bm25(cases) LIMIT ?",
                    (expression, time.time() - 365 * 86400, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT id,request,summary,recipe,evidence,metadata,created FROM cases ORDER BY rowid DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [
            dict(
                zip(
                    (
                        "id",
                        "request",
                        "summary",
                        "recipe",
                        "evidence",
                        "metadata",
                        "created",
                    ),
                    (*row[:5], json.loads(row[5]), float(row[6])),
                )
            )
            for row in rows
        ]

    def delete(self):
        with self.store.connect() as db:
            db.execute("DELETE FROM cases")
            db.execute("DELETE FROM knowledge")
