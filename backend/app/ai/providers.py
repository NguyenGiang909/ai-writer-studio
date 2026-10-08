
"""Provider adapters for AI completion.

Interface: complete(ModelRequest) -> CompletionResult.
- FakeProvider: deterministic local responses for dev/UI testing.
- OpenAICompatibleProvider: real HTTP chat-completions call (OpenAI, OpenRouter, LM Studio...).
"""

import asyncio
import re
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

_FAKE_PREMISE = """{"title": "Truyện Giả Lập", "logline": "Một người lữ khách tìm lại ký ức bị đánh mất.", "premise": "Nhân vật chính tỉnh dậy không còn ký ức, chỉ có một chiếc la bàn lạ. Mỗi trang sách trong thư viện cổ là một mảnh ký ức của ai đó — kể cả của chính anh.", "genre": "huyền bí", "tone": "trầm, suy tư", "themes": ["ký ức", "danh tính"], "target_reader": "người lớn"}"""

_FAKE_CAST = """{"characters": [{"name": "Minh", "role": "protagonist", "summary": "Lữ khách mất ký ức.", "voice_notes": "ít nói", "status": "active", "importance": 5, "aliases": ["người không tên"], "age": "25 tuổi", "context": "lang thang không nghề"}, {"name": "Lão Tạp", "role": "supporting", "summary": "Thủ thư già.", "voice_notes": "nói điệu", "status": "active", "importance": 3, "aliases": [], "age": "70 tuổi", "context": "thủ thư thư viện cổ"}, {"name": "Kẻ Đốp", "role": "antagonist", "summary": "Kẻ trộm ký ức.", "voice_notes": "lạnh", "status": "active", "importance": 4, "aliases": []}], "relationships": [{"a": "Minh", "b": "Lão Tạp", "type": "mentor", "notes": "dẫn đường"}]}"""

_FAKE_WORLD = """{"locations": [{"name": "Thư viện Cổ", "description": "Nơi lưu giữ ký ức dạng sách."}], "factions": [{"name": "Hội Thủ Thư", "description": "Giữ trật tự ký ức."}], "items": [{"name": "La bàn lạ", "description": "Chỉ về phía ký ức mất."}], "abilities": [], "lore": [{"name": "Quy tắc Ký ức", "type": "rule", "description": "Ký ức mất không bao giờ biến mất hẳn."}], "style": {"tone": "trầm", "pov": "ngôi thứ ba", "tense": "quá khứ", "notes": ""}}"""

_FAKE_OUTLINE = """{"volumes": [{"title": "Quyển 1: Mảnh Ký Ức", "arcs": [{"title": "Hồi 1: Tỉnh dậy", "goal": "mở bí ẩn", "chapter_count": 2}]}]}"""

_FAKE_ARC_CHAPTERS = """{"chapters": [{"title": "Chương 1: La bàn", "beat": "Minh tỉnh dậy, tìm thấy la bàn"}, {"title": "Chương 2: Thư viện", "beat": "Minh gặp Lão Tạp"}]}"""

_FAKE_CHAPTER_SCENES = """Đến thư viện — Minh theo la bàn tới cửa thư viện cổ
Gặp Lão Tạp — thủ thư già chặn lại, hỏi lai lịch
Trang sách đầu — Minh đọc được mảnh ký ức đầu tiên"""

_FAKE_CHAPTER_FACTS = """{"timeline_events": [{"event_type": "plot", "event": "Minh tìm thấy la bàn kỳ lạ", "story_time": 1}], "state_changes": [{"entity": "Minh", "field": "knowledge", "old_value": null, "new_value": "KNOWS_La_bàn", "story_time": 1}, {"entity": "Minh", "field": "nơi ở", "old_value": null, "new_value": "thư viện cổ", "story_time": 1}], "thread_touches": [{"thread_title": "Bí ẩn ký ức", "beat_type": "setup", "note": "la bàn chỉ về ký ức mất"}], "canon_facts": [{"subject_type": "story", "predicate": "exists", "value_text": "La bàn chỉ về ký ức đã mất"}], "recap": "Minh tỉnh dậy mất trí nhớ, tìm thấy la bàn kỳ lạ và lần theo nó tới thư viện cổ; ở đó cậu gặp Lão Tạp."}"""

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
        elif task == "chapter_write":
            # gom cả chương: echo mỗi cảnh trong prompt thành 1 block có marker
            titles = re.findall(r"### CẢNH: (.+)", prompt) or ["Một"]
            text = "\n\n".join(
                f"### CẢNH: {t.strip()}\n" + _FAKE_EXPAND.format(
                    heading=t.strip(), model=self.model, prompt_tokens=tokens_in)
                for t in titles)
        elif task in {"discussion", "chat", "brainstorm"}:
            last = next((ln.split(":", 1)[1].strip() for ln in reversed(prompt.splitlines())
                         if ln.strip().lower().startswith(("author:", "user:"))), prompt.strip()[:120])
            text = _FAKE_DISCUSS.format(last=last)
        elif task in {"extraction", "review"}:
            text = _FAKE_EXTRACT
        elif task == "premise":
            text = _FAKE_PREMISE
        elif task == "cast_gen":
            text = _FAKE_CAST
        elif task == "world_gen":
            text = _FAKE_WORLD
        elif task == "book_outline":
            text = _FAKE_OUTLINE
        elif task == "arc_chapters":
            text = _FAKE_ARC_CHAPTERS
        elif task == "chapter_outline":
            text = _FAKE_CHAPTER_SCENES
        elif task == "chapter_facts":
            text = _FAKE_CHAPTER_FACTS
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
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "anthropic": "https://api.anthropic.com",
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
        if "kiraai.vn" in self.base_url:
            # kiraai free tier: reasoning model đốt completion token "nghĩ" ~80tok/s
            # trong khi gateway cắt request >60s → 504. reasoning_effort=low ép
            # thinking ngắn lại, call qua được ngưỡng gateway.
            payload["reasoning_effort"] = "low"
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
                # 4xx + 504/413/408 — fail fast: auth/quota lỗi vĩnh viễn,
                # gateway-timeout/request-quá-nặng retry giống hệt vẫn chết
                if e.response.status_code < 500 or e.response.status_code in (504, 413, 408):
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
        if not (text or "").strip():
            # model dừng ở phần "nghĩ" (reasoning_content) trước khi trả lời —
            # KHÔNG fallback vào reasoning_content (nó là scratchpad, sẽ leak
            # ghi chú planning tiếng Anh vào bản thảo). Báo lỗi để retry/lại brief.
            raise RuntimeError(
                "Model returned empty content — output truncated at reasoning stage")
        return CompletionResult(
            text=text,
            provider=self.name, model=model,
            usage=data.get("usage", {}),
        )


# ---------------------------------------------------------------- anthropic

class AnthropicProvider(BaseProvider):
    """POST /v1/messages — Anthropic Messages API (không tương thích OpenAI)."""

    def __init__(self, api_key: str, model: str, base_url: str, name: str = "anthropic"):
        self.api_key, self.model, self.base_url, self.name = api_key, model, base_url, name

    async def complete(self, request) -> CompletionResult:
        model = request.model or self.model
        payload: dict = {
            "model": model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system:
            payload["system"] = request.system
        last_exc: httpx.HTTPError | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=180) as client:
                    r = await client.post(
                        f"{self.base_url.rstrip('/')}/v1/messages",
                        headers={
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json=payload,
                    )
                r.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    raise
                last_exc = e
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_exc = e
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
        else:
            raise last_exc  # type: ignore[misc]
        data = r.json()
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if isinstance(b, dict) and b.get("type") == "text")
        usage = data.get("usage") or {}
        return CompletionResult(
            text=text,
            provider=self.name, model=model,
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            },
        )
