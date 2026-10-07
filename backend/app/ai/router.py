
"""Model router: task -> model preference -> credential -> provider adapter.

Resolution order (D1):
1. ModelPreference scoped to the request's project.
2. Account-level ModelPreference for the task.
3. Explicit request.model / provider hint.
4. FakeProvider fallback when settings.allow_fake_provider (dev/test).
"""

from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import (
    AnthropicProvider, CompletionResult, FakeProvider, OpenAICompatibleProvider, PROVIDER_ENDPOINTS,
)
from app.core.config import settings
from app.models.account import ModelPreference, ProviderCredential, UsageLog
from app.services.credentials import decrypt_secret

DEV_USER = "local-author"


def build_provider(cred: ProviderCredential, model: str | None = None):
    """Credential -> provider adapter. base_url của credential override endpoint mặc định
    (cho 'custom'/LM Studio/proxy — bắt buộc với provider không có endpoint sẵn)."""
    base = cred.base_url or PROVIDER_ENDPOINTS.get(cred.provider)
    if not base:
        raise RuntimeError(
            f"Provider '{cred.provider}' cần base_url (nhập khi kết nối — vd http://localhost:1234/v1)"
        )
    if not model:
        raise RuntimeError(f"Provider '{cred.provider}' cần tên model (đặt trong Định tuyến model)")
    api_key = decrypt_secret(cred.encrypted_secret)
    if cred.provider == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model or "", base_url=base)
    return OpenAICompatibleProvider(
        api_key=api_key, model=model or "", base_url=base, name=cred.provider
    )


@dataclass
class ModelRequest:
    task: str
    prompt: str
    model: str | None = None
    project_id: str | None = None
    system: str | None = None


class ModelRouter:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def _preference(self, request: ModelRequest) -> ModelPreference | None:
        if self.db is None:
            return None
        rows = list((await self.db.scalars(select(ModelPreference).where(
            ModelPreference.user_id == DEV_USER,
            ModelPreference.task == request.task,
        ))).all())
        proj = next((r for r in rows
                     if request.project_id and r.project_id == request.project_id), None)
        return proj or next((r for r in rows if r.project_id is None), None)

    async def _provider_for(self, request: ModelRequest):
        pref = await self._preference(request)
        if not pref or self.db is None:
            return None, None
        cred = (await self.db.scalars(select(ProviderCredential).where(
            ProviderCredential.user_id == DEV_USER,
            ProviderCredential.provider == pref.provider,
            ProviderCredential.status == "connected",
        ))).first()
        if not cred:
            raise RuntimeError(f"No connected credential for provider '{pref.provider}' — connect in Settings")
        return build_provider(cred, model=request.model or pref.model), pref

    async def _log_usage(self, request: ModelRequest, provider: str,
                         model: str, result: CompletionResult) -> None:
        if self.db is None:
            return
        try:
            usage = result.usage or {}
            self.db.add(UsageLog(
                user_id=DEV_USER, project_id=request.project_id,
                task=request.task, provider=provider, model=model,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
            ))
            await self.db.commit()
        except Exception:
            await self.db.rollback()

    async def complete(self, request: ModelRequest) -> CompletionResult:
        provider, pref = await self._provider_for(request)
        if provider:
            try:
                result = await provider.complete(request)
            except httpx.HTTPError as e:
                raise RuntimeError(f"Provider '{pref.provider}' request failed: {e}")
            await self._log_usage(request, pref.provider, result.model or pref.model, result)
            if not (result.text or "").strip():
                raise RuntimeError(f"Provider '{pref.provider}' returned an empty completion — retry")
            return result
        if settings.allow_fake_provider:
            result = await FakeProvider().complete(request)
            await self._log_usage(request, "fake", result.model or "fake", result)
            if not (result.text or "").strip():
                raise RuntimeError("Provider returned an empty completion — retry")
            return result
        raise RuntimeError("No AI provider configured — connect one in Settings")
