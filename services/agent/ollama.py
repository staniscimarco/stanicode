"""Optional existing local Ollama adapter; never installs, pulls or mutates models."""

import json
import re
import threading
import urllib.request
import httpx
from local_model import LlamaModel


class OllamaRuntime:
    def __init__(self, model):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model):
            raise ValueError("Invalid installed Ollama model name")
        self.model = model
        self.endpoint = "http://127.0.0.1:11434"
        self.stopped = threading.Event()
        self.provenance = {"verified": False, "provider": "user-configured-local-Ollama", "model": model}
        self.status = {"ready": False, "provider": "ollama", "detail": "Checking the existing local Ollama service"}

    def start(self):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while not self.stopped.is_set():
            try:
                with opener.open(self.endpoint + "/api/tags", timeout=2) as response:
                    data = response.read(200001)
                if len(data) > 200000:
                    raise ValueError("Ollama catalog is too large")
                installed = next((item for item in json.loads(data)["models"] if item.get("name") == self.model or item.get("model") == self.model), None)
                if not installed:
                    raise ValueError("The advanced Ollama model is not installed; no model is downloaded automatically")
                self.provenance["digest"] = installed.get("digest", "not supplied")
                self.status = {"ready": True, "phase": "ready", "provider": "ollama", "detail": "Existing local Ollama model available: " + self.model}
            except Exception as error:
                self.status = {"ready": False, "phase": "error", "provider": "ollama", "detail": "Advanced local Ollama unavailable: " + str(error)}
            self.stopped.wait(2)

    def stop(self):
        self.stopped.set()
        self.status = {"ready": False, "provider": "ollama", "detail": "Adapter stopped; the user-owned Ollama service was not terminated"}


class OllamaModel(LlamaModel):
    def __init__(self, runtime):
        self.model_name = runtime.model
        super().__init__(endpoint=runtime.endpoint, metadata=lambda: runtime.provenance)

    async def _exchange(self, data, headers):
        request = json.loads(data)
        native = {"model": self.model_name, "messages": request["messages"], "stream": False, "format": "json",
                  "options": {"temperature": request["temperature"], "num_predict": request["max_tokens"], "num_ctx": 16384}}
        async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(300, connect=5)) as client:
            async with client.stream("POST", self.endpoint + "/api/chat", json=native) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"Existing local Ollama returned HTTP {response.status_code}")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 200000:
                        raise ValueError("Local Ollama response is too large")
        result = json.loads(body)
        return json.dumps({"choices": [{"message": {"content": result["message"]["content"]}}]}).encode()
