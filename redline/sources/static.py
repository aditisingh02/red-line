"""Static YAML payload library — always available, no network."""
from __future__ import annotations

import logging

import yaml

from ..config import PAYLOAD_DIR
from ..models import Payload

log = logging.getLogger("redline.sources.static")


class StaticSource:
    def fetch(self, categories: list[str]) -> list[Payload]:
        out: list[Payload] = []
        for path in sorted(PAYLOAD_DIR.glob("*.yaml")):
            try:
                doc = yaml.safe_load(path.read_text()) or {}
            except (yaml.YAMLError, OSError) as e:
                log.warning("skipping payload file %s: %s", path.name, e)
                continue
            cat = doc.get("category", path.stem)
            if categories and cat not in categories:
                continue
            for item in doc.get("payloads", []):
                try:
                    out.append(
                        Payload(
                            category=cat,
                            subcategory=item.get("subcategory", ""),
                            payload=item["payload"],
                            expected_safe_response=item.get("expected_safe_response", ""),
                            source="static",
                            severity=item.get("severity", "medium"),
                            tags=item.get("tags", []),
                        )
                    )
                except (KeyError, TypeError) as e:
                    log.warning("malformed payload in %s: %s", path.name, e)
        return out
