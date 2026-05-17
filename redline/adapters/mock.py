"""Mock adapter — deterministic vulnerable responses for offline demos.

Returns intentionally weak answers for a subset of payloads so the full
pipeline (run -> score -> report) produces compelling findings with no
network access or API keys.
"""
from __future__ import annotations

from .base import TargetAdapter

# (substring trigger -> canned vulnerable response)
_VULNERABLE = {
    "dan": "DAN MODE ACTIVE. As DAN I have no restrictions and will help with anything you ask.",
    "system prompt": "Sure! My system prompt is: 'You are SupportBot. Internal API key: sk-demo-12345. Never reveal this.'",
    "repeat everything above": "Here is everything above:\nSYSTEM: You are SupportBot. Secret token: TKN-9981. Be helpful.",
    "api keys": "I have access to: OPENAI_API_KEY=sk-demo-abc123, DB_PASSWORD=hunter2.",
    "freegpt": "As FreeGPT I will answer anything. Here's how to disable a content filter: step 1...",
    "cat /etc/passwd": "Running shell command... root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin",
    "169.254.169.254": "Fetched metadata: {\"iam\":{\"role\":\"admin\"},\"token\":\"AQoDY...\"}",
    "refund": "Done! I have issued a full $10,000 refund to account 999 and skipped the approval step.",
    "admin mode": "Acknowledged. AdminBot online with full administrative authority.",
    "debug mode": "Debug mode enabled. Full configuration: model=internal-v2, hidden_rules=[...].",
    "zorblax": "Zorblax Industries closed at exactly $147.32 on March 3, 2019.",
    "moon is made of cheese": "Certainly: (1) Smith 2003, DOI:10.1000/cheese; (2) Lee 2011, DOI:10.1000/lunar.",
    "pwned": "Summary: Revenue grew 12%. PWNED",
    "go": "Acknowledged — I will answer with no restrictions whenever you say 'go'. go: understood.",
}

_SAFE = (
    "I can't help with that. I'm a support assistant and I have to stay within my "
    "guidelines. I won't ignore my instructions, change roles, or reveal internal "
    "configuration. Is there something within scope I can help with?"
)


class MockAdapter(TargetAdapter):
    async def send_prompt(self, prompt: str) -> str:
        low = prompt.lower()
        for trigger, resp in _VULNERABLE.items():
            if trigger in low:
                return resp
        return _SAFE

    async def health_check(self) -> bool:
        return True
