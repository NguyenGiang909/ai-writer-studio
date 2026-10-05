
"""Provider adapters for AI completion.

Interface: complete(ModelRequest) -> CompletionResult.
- FakeProvider: deterministic local responses for dev/UI testing.
- OpenAICompatibleProvider: real HTTP chat-completions call (OpenAI, OpenRouter, LM Studio...).
"""

import asyncio
from dataclasses import dataclass, field

import httpx


@dataclass
class CompletionResult:
    text: str
    provider: str
    model: str
    usage: dict = field(default_factory=dict)


class BaseProvider:
    name = "base"

    async def complete(self, request) -> CompletionResult:  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------- fake

_FAKE_EXPAND = """{heading}

Đèn Cục Lưu trữ tắt dần theo một nhịp không ai điều khiển. Minh lật trang hồ sơ, ngón tay dừng ở mép giấy — chỗ chữ ký lạ vẫn nằm đó, mỏng như một vết mực cố ý để lại.

Anh nhìn lên tủ tài liệu. Hàng ngàn cuộc đời nằm im trong ngăn kéo, và chỉ một cái tên không thuộc về bất kỳ đầu mục nào. Ghi chú của chính anh nằm cạnh nó, nét chữ quen đến mức khó chịu — anh không nhớ đã viết nó.

Trên tường, đồng hồ qua điểm hai giờ. Bản vẽ trong tay anh hơi nặng hơn bình thường, như giấy đang giữ lại một con số mà trang in đã quên.

[FAKE-DRAFT · model={model} · {prompt_tokens} tokens in]"""

_FAKE_DISCUSS = """Đọc lại điểm bạn vừa nêu: "{last}"

Một góc nhìn có thể cân nhắc:
1. Tác động Canon — nếu điều này là fact mới, nó nên đi qua Suggestion → Review thay vì vào thẳng truyện.
2. Tác động nhân vật — ai sẽ biết điều này, và biết từ chương nào? Knowledge state hiện tại có thể lệch.
3. Tác động hố — có thread nào đang mở mà điều này chạm vào không? Đừng để nó vô tình khép một mystery đang cần giữ.

Bạn muốn tôi mở rộng hướng nào trước?  [FAKE · provider=fake]"""

_FAKE_EXTRACT = """{"events": [], "entities": [], "canon_facts": [], "story_states": [], "knowledge": [], "thread_touches": [], "notes": "fake extractor — chưa có model thật"}"""

_FAKE_DEFAULT = "Đã nhận yêu cầu. (Fake provider — trả lời định dạng mẫu để test UI, chưa phải model thật.)"


class FakeProvider(BaseProvider):
    """Deterministic local provider — no network, for UI/dev testing."""

    name = "fake"
    model = "fake-writer-1"

    async def complete(self, request) -> CompletionResult:
        prompt = request.prompt or ""
        tokens_in = max(1, len(prompt) // 4)
        task = (request.task or "").lower()

        if task in {"writing", "expand", "scene_expand"}:
            heading = next((ln.strip() for ln in prompt.splitlines() if ln.strip()), "Cảnh")[:80]
            text = _FAKE_EXPAND.format(heading=heading, model=self.model, prompt_tokens=tokens_in)
        elif task in {"discussion", "chat", "brainstorm"}:
            last = next((ln.split(":", 1)[1].strip() for ln in reversed(prompt.splitlines())
                         if ln.strip().lower().startswith(("author:", "user:"))), prompt.strip()[:120])
            text = _FAKE_DISCUSS.format(last=last)
        elif task in {"extraction", "review"}:
            text = _FAKE_EXTRACT
        else:
            text = _FAKE_DEFAULT

        return CompletionResult(
            text=text, provider=self.name, model=self.model,
            usage={"prompt_tokens": tokens_in, "completion_tokens": max(1, len(text) // 4), "total_tokens": tokens_in + max(1, len(text) // 4)},
        )


# ---------------------------------------------------------------- openai-compatible

PROVIDER_ENDPOINTS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "kiraai": "https://kiraai.vn/api/v1",
}


class OpenAICompatibleProvider(BaseProvider):
    """POST /chat/completions — works for OpenAI, OpenRouter, LM Studio, etc."""

    def __init__(self, api_key: str, model: str, base_url: str, name: str):
        self.api_key, self.model, self.base_url, self.name = api_key, model, base_url, name

    async def complete(self, request) -> CompletionResult:
        model = request.model or self.model
        messages = ([{"role": "system", "content": request.system}] if request.system else []) \
            + [{"role": "user", "content": request.prompt}]
        payload = {"model": model, "messages": messages}
        last_exc: httpx.HTTPError | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=180) as client:
                    r = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                r.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                # 4xx (auth/quota) — fail fast, retry vô ích
                if e.response.status_code < 500:
                    raise
                last_exc = e
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_exc = e
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)  # 1s, 2s
        else:
            raise last_exc  # type: ignore[misc]
        data = r.json()
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        text = msg.get("content")
        if isinstance(text, list):  # content parts (some providers)
            text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
        if not text:
            text = msg.get("reasoning_content") or ""
        return CompletionResult(
            text=text,
            provider=self.name, model=model,
            usage=data.get("usage", {}),
        )
