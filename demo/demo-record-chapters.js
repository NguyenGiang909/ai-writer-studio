// Quay phần 4: tiếp tục auto-approve các gate → chapters xuất hiện
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const API = 'http://127.0.0.1:8001/api/v1';
const PID = 'a2c609cc-1d28-4ff2-8dec-28a5b31bcd85';
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

  await page.goto(`${BASE}/projects/${PID}/authoring`, { waitUntil: 'networkidle' });
  await wait(3000);

  let last = '';
  for (let i = 0; i < 150; i++) {
    await wait(2000);
    const st = await page.request.get(`${API}/projects/${PID}/authoring/status`);
    if (st.ok()) {
      const j = await st.json();
      const run = j.run || j;
      const s = `${run.phase}|${run.status}`;
      if (s !== last) { console.log('tick:', s); last = s; }
      if (['done', 'complete', 'failed'].includes(run.status) && i > 5) break;
      if (run.status === 'awaiting_review' && i > 3) {
        const a = await page.request.post(`${API}/projects/${PID}/authoring/approve`, { data: {} });
        console.log('  approve->', (await a.text()).slice(0, 90));
      }
    }
    if (i % 4 === 0) await page.mouse.wheel(0, 300);
  }

  await page.goto(`${BASE}/projects/${PID}`, { waitUntil: 'networkidle' });
  await wait(3000);
  const sl = page.locator('a[href*="scene="]').first();
  if (await sl.count()) { await sl.click(); await wait(2500); await page.mouse.wheel(0, 400); await wait(1200); }

  await ctx.close();
  await browser.close();

  const files = fs.readdirSync(OUT).filter(f => f.endsWith('.webm'))
    .map(f => ({ f, t: fs.statSync(path.join(OUT, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  if (files.length) {
    const dst = path.join(OUT, 'ai-writer-chapters-live.webm');
    fs.renameSync(path.join(OUT, files[0].f), dst);
    console.log('VIDEO:', dst, (fs.statSync(dst).size / 1048576).toFixed(1) + 'MB');
  }
})().catch(e => { console.error(e); process.exit(1); });
