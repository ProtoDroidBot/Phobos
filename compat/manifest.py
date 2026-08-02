"""Extraction manifest and strict-mode result tracking."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone


class ExtractionManifest:
    SCHEMA_VERSION = 1

    def __init__(self, client_profile=None):
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at = None
        self.client = client_profile.as_dict() if client_profile is not None else None
        self.containers = []

    def record(self, miner, container, status, backend=None, error=None, output=None, source=None):
        item = {
            "miner": miner,
            "container": container,
            "status": status,
        }
        if backend:
            item["backend"] = backend
        if error:
            item["error"] = error
        if output:
            item["output"] = output
        if source:
            item["source"] = source
        self.containers.append(item)

    @property
    def failures(self):
        return [item for item in self.containers if item["status"] == "failed"]

    def as_dict(self):
        counts = Counter(item["status"] for item in self.containers)
        return {
            "schemaVersion": self.SCHEMA_VERSION,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "client": self.client,
            "summary": dict(sorted(counts.items())),
            "containers": self.containers,
        }

    def write(self, output_folder, filename="_phobos_manifest.json"):
        self.finished_at = datetime.now(timezone.utc).isoformat()
        os.makedirs(output_folder, exist_ok=True)
        path = os.path.join(output_folder, filename)
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(self.as_dict(), stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        return path
