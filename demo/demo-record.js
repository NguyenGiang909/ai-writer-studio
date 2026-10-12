// Quay tour AI Writer Studio — playwright video -> demo/video/*.webm
// Chạy: node demo-record.js   (cần backend :8001 + frontend :3000)
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const API = 'http://127.0.0.1:8001/api/v1';
const BIG_PID = 'e9b5cb1c-c075-4f55-89ae-53deba347937'; // Những Cuộc Tình Tải Xuống
const OUT = 'D:/Devin.Ai/AI writer/ai-writer-studio-recovery-m10/demo/video';

const wait = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    recordVideo: { dir: OUT, size: { width: 1600, height: 900 } },
    locale: 'vi-VN',
  });
  const page = await ctx.newPage();

  // 1. Home — danh sách project
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await wait(2200);

  // 2. Mở truyện lớn 69 chương — manuscript tree
  await page.goto(`${BASE}/projects/${BIG_PID}`, { waitUntil: 'networkidle' });
  await wait(2500);
  // Cuộn cây bản thảo để thấy quy mô 69 chương
  for (let i = 0; i < 6; i++) {
    await page.mouse.wheel(0, 600);
    await wait(500);
  }
  // Cuộn ngược lên
  await page.mouse.wheel(0, -4000);
  await wait(900);

  // 3. Mở 1 cảnh — prose thật do máy viết
  const sceneLink = page.locator('a[href*="scene="]').first();
  if (await sceneLink.count()) {
    await sceneLink.click();
    await wait(2500);
    await page.mouse.wheel(0, 500);
    await wait(1200);
    await page.mouse.wheel(0, 500);
    await wait(1200);
  }

  // 4. Trang Review — audit findings
  await page.goto(`${BASE}/projects/${BIG_PID}/review`, { waitUntil: 'networkidle' });
  await wait(2800);
  await page.mouse.wheel(0, 500);
  await wait(1500);

  // 5. Timeline
  await page.goto(`${BASE}/projects/${BIG_PID}/timeline`, { waitUntil: 'networkidle' });
  await wait(2500);

  // 6. Authoring room của run đã xong 69/69
  await page.goto(`${BASE}/projects/${BIG_PID}/authoring`, { waitUntil: 'networkidle' });
  await wait(2500);

  // 7. TẠO PROJECT MỚI + chạy authoring fake-provider trước mắt
  const resp = await page.request.post(`${API}/projects`, { data: { name: 'Demo — Máy Viết Trực Tiếp' } });
  const demo = await resp.json();
  await page.goto(`${BASE}/projects/${demo.id}/authoring`, { waitUntil: 'networkidle' });
  await wait(2000);

  // Đặt target 3 chương rồi start — tìm nút bắt đầu run
  // UI authoring: nút kiểu "Bắt đầu" / "Chạy" — thử các selector phổ biến
  const startBtn = page.locator('button:has-text("Bắt đầu"), button:has-text("Chạy"), button:has-text("Start"), button:has-text("Viết")').first();
  if (await startBtn.count()) {
    await startBtn.click();
    await wait(1500);
  }
  // Poll run qua API, chờ các bước tick; giao diện tự cập nhật
  for (let i = 0; i < 45; i++) {
    await wait(2000);
    const st = await page.request.get(`${API}/projects/${demo.id}/authoring/run`);
    if (st.ok()) {
      const j = await st.json();
      if (j && j.status && j.status !== 'running' && j.status !== 'pending') break;
      if (i % 5 === 0) await page.mouse.wheel(0, 300); // nhích để thấy progress
    }
  }
  // Show kết quả: manuscript tree đã có chương
  await page.goto(`${BASE}/projects/${demo.id}`, { waitUntil: 'networkidle' });
  await wait(3000);

  // 8. Search nhanh "tình" trên truyện lớn
  await page.goto(`${BASE}/projects/${BIG_PID}/search?q=tình`, { waitUntil: 'networkidle' });
  await wait(2500);

  await ctx.close(); // quan trọng: finalize webm
  await browser.close();

  // Đổi tên video mới nhất
  const files = fs.readdirSync(OUT).filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (files.length) {
    const dst = path.join(OUT, 'ai-writer-demo.webm');
    fs.renameSync(path.join(OUT, files[0].f), dst);
    console.log('VIDEO:', dst, (fs.statSync(dst).size / 1048576).toFixed(1) + 'MB');
  }
})().catch(e => { console.error(e); process.exit(1); });
