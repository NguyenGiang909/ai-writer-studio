// Quay phần 2: authoring engine viết live — project rỗng → 3 chương
// Chạy: node demo-record2.js
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const API = 'http://127.0.0.1:8001/api/v1';
const PID = 'a2c609cc'; // project "Demo — Máy Viết Trực Tiếp" đã tạo
const OUT = 'D:/Devin.Ai/AI writer/ai-writer-studio-recovery-m10/demo/video';
const wait = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    recordVideo: { dir: OUT, size: { width: 1600, height: 900 } },
    locale: 'vi-VN',
  });
  const page = await ctx.newPage();

  // resolve full pid
  const projs = await (await page.request.get(`${API}/projects`)).json();
  const demo = projs.find(p => p.id.startsWith(PID));
  if (!demo) throw new Error('demo project not found');
  console.log('demo:', demo.id, demo.name);

  // Mở trang authoring (trống) — viewer thấy project chưa có gì
  await page.goto(`${BASE}/projects/${demo.id}/authoring`, { waitUntil: 'networkidle' });
  await wait(2500);

  // Bắn run qua API — fake provider tick từng step, UI poll tự cập nhật
  const r = await page.request.post(`${API}/projects/${demo.id}/authoring/start`, {
    data: {
      prompt: 'Một lập trình viên thất nghiệp nhận được email từ chính mình ở tương lai, cảnh báo đừng deploy bản build tối nay.',
      target_chapters: 3,
      words_per_scene: 400,
      call_mode: 'safe',
      flow: 'rolling',
      goal_mode: 'end',
    },
  });
  console.log('start:', r.status(), (await r.text()).slice(0, 160));

  // Xem run tick — poll status, khi xong hoặc hết giờ thì dừng quay
  let lastPhase = '';
  for (let i = 0; i < 90; i++) {
    await wait(2000);
    const st = await page.request.get(`${API}/projects/${demo.id}/authoring/status`);
    if (st.ok()) {
      const j = await st.json();
      const ph = `${j.phase}|${j.status}|ch${j.chapters_done ?? '?'}`;
      if (ph !== lastPhase) { console.log('tick:', ph); lastPhase = ph; }
      if (['done', 'failed', 'awaiting_review'].includes(j.status) && i > 8) break;
    }
    if (i % 6 === 0) await page.mouse.wheel(0, 350); // nhích cho video sống
  }

  // Mở manuscript — cây đã có chương/cảnh do máy viết
  await page.goto(`${BASE}/projects/${demo.id}`, { waitUntil: 'networkidle' });
  await wait(3000);
  // Mở cảnh đầu để thấy prose
  const sl = page.locator('a[href*="scene="]').first();
  if (await sl.count()) { await sl.click(); await wait(2500); }

  await ctx.close();
  await browser.close();

  const files = fs.readdirSync(OUT).filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (files.length) {
    const dst = path.join(OUT, 'ai-writer-authoring-live.webm');
    fs.renameSync(path.join(OUT, files[0].f), dst);
    console.log('VIDEO:', dst, (fs.statSync(dst).size / 1048576).toFixed(1) + 'MB');
  }
})().catch(e => { console.error(e); process.exit(1); });
