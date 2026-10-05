---
name: github
description: Git and GitHub workflows for this project — init repo, commit, push, branches, PRs. Use when the user mentions github, git, commit, push, repo, đẩy code, sao lưu lên github, PR, pull request, branch, merge.
---

# Git / GitHub — Story OS

Project gốc ở `E:\AI writer\ai-writer-studio-recovery-m10` — **chưa phải git repo** lần cuối kiểm tra. `git` đã cài, `gh` CLI **chưa cài** (cài: `winget install GitHub.cli`).

## Tuyệt đối không commit

Kiểm tra `.gitignore` trước mọi `git init`/`git add`:

```
backend/.venv/  node_modules/  .next/
backend/writer.db           # dữ liệu thật của user
frontend/.env.local         # trỏ API cục bộ
**/*.log  __pycache__/
*.pem *.key  .env           # secrets / BYOK keys
```

- BYOK provider keys nằm trong DB/secret store — **không export ra file** để commit.
- Trước khi `git add -A`: `git status` rà file lạ, grep nhanh `api_key|sk-|secret` trong các file sắp stage.

## Lần đầu đưa project lên GitHub

1. `git init` (trong thư mục project), tạo/kiểm `.gitignore` theo block trên.
2. Commit đầu: `git add -A && git commit -m "chore: initial import — writer story OS"`.
3. Remote:
   - Có `gh`: `gh repo create <name> --private --source=. --push` (mặc định **private** — đây là dự án cá nhân).
   - Không `gh`: user tự tạo repo trên web → `git remote add origin https://github.com/<user>/<repo>.git && git push -u origin main`.
4. Đặt `git branch -M main` nếu cần.

## Commit hàng ngày

1. Chạy song song: `git status`, `git diff`, `git log -5` (bắt chước style commit cũ; repo mới → conventional: `feat:`, `fix:`, `chore:`).
2. Message ngắn, nói **lý do** không liệt kê file; tiếng Việt hay Anh đều được — theo repo hiện có.
3. Footer:

   ```
   Generated with [Devin](https://devin.ai)
   Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>
   ```

4. Không commit khi không có gì đổi; không sửa git config; không `-i`.

## Cấm (trừ khi user bảo rõ)

- `git push` khi chưa được yêu cầu.
- Force-push, `reset --hard` qua commit của người khác, xoá branch, checkout đè lên thay đổi chưa commit.
- Sửa lịch sử đã push (rebase/amend commit public).

## Workflow feature lớn

- `git checkout -b feat/<ten-ngan>` → commit nhỏ → push → `gh pr create` (nếu có `gh`, nếu không user mở PR trên web).
- Repo solo + user không nhắc branch → commit thẳng `main` cũng được, hỏi một lần rồi nhớ.

## Kiểm tra trước khi commit

- Backend đổi: `.venv/Scripts/python.exe -m pytest tests/ -x -q` tại `backend/`.
- Frontend đổi: `npx tsc --noEmit` tại `frontend/`.
- Không chặn commit vì warning, chỉ chặn khi fail.

## Lưu ý môi trường

- Windows: path có space → luôn quote; shell là Git Bash — `rm`/`ls` dùng được, `del` không.
- Uvicorn đang chạy giữ file `writer.db` và `.venv` — có trong `.gitignore` nên không ảnh hưởng commit.
