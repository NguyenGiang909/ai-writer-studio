import os, secrets
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def data_dir() -> Path:
    """Thư mục dữ liệu theo OS — %LOCALAPPDATA%/AIWriterStudio trên Windows,
    XDG_DATA_HOME/… trên Linux/macOS. Dùng khi đóng gói (không ghi vào cwd)."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    d = Path(base) / "AIWriterStudio"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_or_make_secret(path: Path) -> str:
    if path.exists():
        return path.read_text().strip()
    key = secrets.token_urlsafe(32)
    path.write_text(key)
    return key


class Settings(BaseSettings):
    app_name: str = "AI Writer Studio"
    environment: str = "development"
    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = ""
    allow_fake_provider: bool | None = None
    build_id: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def model_post_init(self, _ctx) -> None:
        prod = self.environment != "development"
        if self.allow_fake_provider is None:
            # dev/test: cho phép FakeProvider (không cần key). Bản đóng gói:
            # TẮT — không key phải báo lỗi rõ, không trả văn giả thầm lặng.
            self.allow_fake_provider = not prod
        if not self.build_id:
            # stamp do build_package.ps1 ghi — /health trả về để đối chiếu.
            # Frozen (PyInstaller): file nằm cạnh .exe; dev: nằm ở repo root.
            import sys
            base = (Path(sys.executable).parent if getattr(sys, "frozen", False)
                    else Path(__file__).parent.parent.parent.parent)
            try:
                self.build_id = (base / "build_id.txt").read_text().strip()
            except OSError:
                self.build_id = "dev"
        if not self.database_url:
            self.database_url = (
                f"sqlite+aiosqlite:///{(data_dir() / 'writer.db').as_posix()}"
                if prod else "sqlite+aiosqlite:///./writer.db")
        if not self.secret_key:
            if prod:
                # Fernet key phải bền qua restart — sinh 1 lần, lưu cạnh DB
                self.secret_key = _load_or_make_secret(data_dir() / "secret.key")
            else:
                self.secret_key = "dev-insecure-key-change-me"
        elif prod and self.secret_key == "dev-insecure-key-change-me":
            raise RuntimeError("secret_key mặc định không được dùng ngoài development")


settings = Settings()
