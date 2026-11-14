/**
 * Record portfolio MP4s of the live duihua UI (Playwright + ffmpeg GIFs).
 *
 * Usage (dev server already on :5173, API on :8000):
 *   node scripts/portfolio/record.mjs
 */
import { chromium } from "../../frontend/node_modules/@playwright/test/index.mjs";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");
const OUT = path.join(ROOT, "docs/portfolio");
const RAW = path.join(OUT, "_raw");
const BASE = "http://127.0.0.1:5173/?demo=portfolio";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function enrich(text, topicId = null) {
  const res = await fetch("http://127.0.0.1:8000/api/enrich", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, topic_id: topicId, repair: true }),
  });
  if (!res.ok) throw new Error(`enrich failed: ${res.status}`);
  return res.json();
}

async function seedConversation(page) {
  const ai = await enrich("你家有几口人？跟我说一说你的家人吧。", "family");
  const user = await enrich("我家有三口人。", "family");
  const ai2 = await enrich("真好！你有哥哥或者姐姐吗？", "family");

  await page.evaluate(
    ({ ai, user, ai2 }) => {
      const store = window.__DUIHUA_STORE__;
      if (!store) throw new Error("store not exposed — open with ?demo=portfolio");
      store.getState().setTheme("light");
      store.getState().setLevel(10);
      store.getState().setTopicId("family");
      store.getState().setSessionId(1);
      store.getState().setView("chat");
      store.getState().setMessages([
        {
          id: 1,
          session_id: 1,
          role: "assistant",
          text: ai.text,
          tokens: ai.tokens,
          translation: "How many people in your family? Tell me about them.",
          correction: null,
          created_at: new Date().toISOString(),
        },
        {
          id: 2,
          session_id: 1,
          role: "user",
          text: user.text,
          tokens: user.tokens,
          translation: "There are three people in my family.",
          correction: {
            better: "我家有三口人。",
            reason: "Natural family-size phrasing uses 口 as the measure word.",
          },
          created_at: new Date().toISOString(),
          heard_raw: "我借口有三人",
        },
        {
          id: 3,
          session_id: 1,
          role: "assistant",
          text: ai2.text,
          tokens: ai2.tokens,
          translation: "Nice! Do you have an older brother or sister?",
          correction: null,
          created_at: new Date().toISOString(),
        },
      ]);
    },
    { ai, user, ai2 },
  );
}

async function waitStore(page) {
  await page.waitForFunction(() => Boolean(window.__DUIHUA_STORE__), null, {
    timeout: 15_000,
  });
}

async function recordClip(browser, name, size, run) {
  const context = await browser.newContext({
    viewport: size,
    recordVideo: { dir: RAW, size },
    deviceScaleFactor: size.width >= 1200 ? 1 : 2,
  });
  const page = await context.newPage();
  await page.goto(BASE, { waitUntil: "networkidle" });
  await waitStore(page);
  await run(page);
  await sleep(600);
  await context.close();
  // Playwright names the file after the page; find newest webm in RAW
  const { readdirSync, statSync, renameSync } = await import("node:fs");
  const files = readdirSync(RAW)
    .filter((f) => f.endsWith(".webm"))
    .map((f) => ({ f, m: statSync(path.join(RAW, f)).mtimeMs }))
    .sort((a, b) => b.m - a.m);
  if (!files.length) throw new Error(`no video for ${name}`);
  const destWebm = path.join(RAW, `${name}.webm`);
  renameSync(path.join(RAW, files[0].f), destWebm);
  return destWebm;
}

function toMp4AndGif(webmPath, basename) {
  const mp4 = path.join(OUT, `${basename}.mp4`);
  const gif = path.join(OUT, `${basename}.gif`);
  const poster = path.join(OUT, `${basename}.png`);

  const mp4r = spawnSync(
    "ffmpeg",
    [
      "-y",
      "-i",
      webmPath,
      "-an",
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "+faststart",
      mp4,
    ],
    { encoding: "utf8" },
  );
  if (mp4r.status !== 0) {
    console.error(mp4r.stderr);
    throw new Error(`ffmpeg mp4 failed for ${basename}`);
  }

  const pal = path.join(RAW, `${basename}-palette.png`);
  spawnSync(
    "ffmpeg",
    [
      "-y",
      "-i",
      mp4,
      "-vf",
      "fps=12,scale=960:-1:flags=lanczos,palettegen=stats_mode=diff",
      pal,
    ],
    { encoding: "utf8" },
  );
  const gifr = spawnSync(
    "ffmpeg",
    [
      "-y",
      "-i",
      mp4,
      "-i",
      pal,
      "-lavfi",
      "fps=12,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
      "-loop",
      "0",
      gif,
    ],
    { encoding: "utf8" },
  );
  if (gifr.status !== 0) {
    console.error(gifr.stderr);
    throw new Error(`ffmpeg gif failed for ${basename}`);
  }

  spawnSync(
    "ffmpeg",
    ["-y", "-ss", "2.8", "-i", mp4, "-frames:v", "1", poster],
    { encoding: "utf8" },
  );

  return { mp4, gif, poster };
}

async function main() {
  await mkdir(OUT, { recursive: true });
  await mkdir(RAW, { recursive: true });

  const only = process.env.PORTFOLIO_ONLY?.split(",").map((s) => s.trim()).filter(Boolean);

  const health = await fetch("http://127.0.0.1:5173/").then((r) => r.status).catch(() => 0);
  const api = await fetch("http://127.0.0.1:8000/readyz").then((r) => r.status).catch(() => 0);
  if (health !== 200 || api !== 200) {
    throw new Error("Start the app first (`make dev`) — need :5173 and :8000");
  }

  const browser = await chromium.launch({ headless: true });
  const desktop = { width: 1440, height: 900 };
  const want = (name) => !only || only.includes(name);

  let webm;
  if (want("01-conversation")) {
    console.log("Recording 01-conversation…");
    webm = await recordClip(browser, "01-conversation", desktop, async (page) => {
      await seedConversation(page);
      await sleep(900);
      const word = page.getByRole("button", { name: /有 yǒu|你家/ }).first();
      if (await word.count()) {
        await word.click();
        await sleep(800);
      } else {
        await page.locator("main button").filter({ hasText: /有|家|人/ }).first().click();
        await sleep(800);
      }
      const save = page.getByRole("button", { name: /Save/ });
      if (await save.isVisible().catch(() => false)) {
        await save.click();
        await sleep(700);
      }
      await page.getByRole("button", { name: /^Pinyin/ }).click();
      await sleep(400);
      await page.getByRole("button", { name: /^Pinyin/ }).click();
      await sleep(400);
      await page.getByRole("button", { name: /^English/ }).click();
      await sleep(500);
      await page.getByRole("button", { name: /^English/ }).click();
      await sleep(700);
    });
    toMp4AndGif(webm, "01-conversation");
  }

  if (want("02-topics")) {
    console.log("Recording 02-topics…");
    webm = await recordClip(browser, "02-topics", desktop, async (page) => {
      await page.getByRole("button", { name: /Topics/ }).click();
      await sleep(900);
      await page.mouse.wheel(0, 400);
      await sleep(600);
      await page.mouse.wheel(0, -200);
      await sleep(400);
      const family = page.getByRole("button", { name: /family|家人|Family/i }).first();
      if (await family.count()) {
        await family.click();
      } else {
        await page.locator("main button").first().click();
      }
      await sleep(1800);
      await page.mouse.wheel(0, 120);
      await sleep(900);
    });
    toMp4AndGif(webm, "02-topics");
  }

  if (want("03-tour")) {
    console.log("Recording 03-tour…");
    webm = await recordClip(browser, "03-tour", desktop, async (page) => {
      await seedConversation(page);
      await sleep(700);
      await page.getByRole("button", { name: /Topics/ }).click();
      await sleep(800);
      await page.getByRole("button", { name: /Saved words/ }).click();
      await sleep(900);
      await page.getByRole("button", { name: /Progress/ }).click();
      await sleep(900);
      await page.getByRole("button", { name: /^Chat/ }).click();
      await sleep(700);
      await page.getByRole("button", { name: /Dark|Light|深色|浅色/ }).click();
      await sleep(900);
      await page.getByRole("button", { name: /Dark|Light|深色|浅色/ }).click();
      await sleep(700);
    });
    toMp4AndGif(webm, "03-tour");
  }

  if (want("04-review-before-send")) {
    console.log("Recording 04-review-before-send…");
    webm = await recordClip(browser, "04-review-before-send", desktop, async (page) => {
      const ai = await enrich("你家有几口人？跟我说一说你的家人吧。", "family");
      const repaired = await enrich("我借口有三人", "family");
      await page.evaluate(({ ai }) => {
        const state = window.__DUIHUA_STORE__.getState();
        state.setTheme("light");
        state.setLevel(10);
        state.setTopicId("family");
        state.setSessionId(1);
        state.setView("chat");
        if (!state.reviewBeforeSend) state.toggleReviewBeforeSend();
        state.setMessages([
          {
            id: 1,
            session_id: 1,
            role: "assistant",
            text: ai.text,
            tokens: ai.tokens,
            translation: "How many people in your family? Tell me about them.",
            correction: null,
            created_at: new Date().toISOString(),
          },
        ]);
      }, { ai });
      await page.waitForFunction(() => typeof window.__DUIHUA_SET_REVIEW__ === "function");
      await page.evaluate((repaired) => {
        window.__DUIHUA_SET_REVIEW__({
          text: repaired.text,
          tokens: repaired.tokens,
          translation: "There are three people in my family.",
          pinyinLine: repaired.pinyin_line,
          originalText: repaired.original_text || "我借口有三人",
          repairNote: repaired.repair_note || "Adjusted to fit this topic",
        });
      }, repaired);
      await sleep(900);
      await page
        .getByText(/Adjusted to fit|我家有三口人|我借口有三人/)
        .first()
        .scrollIntoViewIfNeeded();
      await sleep(1000);
      const reviewSend = page.locator("button[type='button']", { hasText: "Send ·" });
      await page.getByRole("button", { name: /^Discard/ }).hover();
      await sleep(600);
      await reviewSend.first().hover();
      await sleep(1400);
    });
    toMp4AndGif(webm, "04-review-before-send");
  }

  if (want("05-mobile")) {
    console.log("Recording 05-mobile…");
    webm = await recordClip(
      browser,
      "05-mobile",
      { width: 390, height: 844 },
      async (page) => {
        await seedConversation(page);
        await sleep(1000);
        await page.getByRole("button", { name: /^Topics$/ }).click();
        await sleep(900);
        await page.getByRole("button", { name: /^Chat$/ }).click();
        await sleep(800);
        const word = page.locator("main button").filter({ hasText: /有|家|人/ }).first();
        if (await word.count()) {
          await word.click();
          await sleep(1000);
        }
      },
    );
    toMp4AndGif(webm, "05-mobile");
  }

  if (!only) {
    console.log("Capturing stills…");
    const context = await browser.newContext({
      viewport: desktop,
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    await page.goto(BASE, { waitUntil: "networkidle" });
    await waitStore(page);
    await seedConversation(page);
    await sleep(500);
    await page.screenshot({ path: path.join(OUT, "still-chat.png"), fullPage: false });
    await page.getByRole("button", { name: /Topics/ }).click();
    await sleep(500);
    await page.screenshot({ path: path.join(OUT, "still-topics.png"), fullPage: false });
    await page.getByRole("button", { name: /Progress/ }).click();
    await sleep(500);
    await page.screenshot({ path: path.join(OUT, "still-progress.png"), fullPage: false });
    await context.close();
  }
  await browser.close();

  const readme = `# duihua · portfolio media

Product demos of **duihua 对话** — a personal Mandarin speaking coach (voice + rich transcript).

Generated with Playwright against the live local app. Re-record anytime:

\`\`\`bash
make dev   # in one terminal
node scripts/portfolio/record.mjs
\`\`\`

## Clips

| File | What it shows |
|------|----------------|
| \`01-conversation.mp4\` / \`.gif\` | Stacked pinyin · hanzi · English, word tap → dictionary, save word |
| \`02-topics.mp4\` / \`.gif\` | Browse scenarios and start a topic role-play |
| \`03-tour.mp4\` / \`.gif\` | Chat · Topics · Saved words · Progress + theme toggle |
| \`04-review-before-send.mp4\` / \`.gif\` | Review transcript before send, with topic-aware STT repair |
| \`05-mobile.mp4\` / \`.gif\` | Same product on a phone-sized viewport |

Stills: \`still-chat.png\`, \`still-topics.png\`, \`still-progress.png\`, plus a mid-clip \`.png\` poster per video.

## Portfolio tips

- Prefer **MP4** for project pages / case studies (sharper, smaller).
- Prefer **GIF** for README embeds and quick LinkedIn/Twitter previews.
- Suggested caption: *“Speak Mandarin with live pinyin, hanzi, and English — plus topic role-play and review-before-send.”*
`;

  await writeFile(path.join(OUT, "README.md"), readme);
  console.log(`\nDone → ${OUT}`);
  for (const f of [
    "01-conversation",
    "02-topics",
    "03-tour",
    "04-review-before-send",
    "05-mobile",
  ]) {
    console.log(`  ${f}.mp4  ${f}.gif`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
