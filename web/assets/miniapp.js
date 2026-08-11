/* منطق مینی‌اپ تلگرام (library + viewer) — فایل اصلی هیچ‌وقت به کلاینت نمی‌رسه */

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  // احترام به تم تلگرام
  if (tg.colorScheme === "dark") document.documentElement.dataset.theme = "dark";
}

let TOKEN = null;

document.addEventListener("DOMContentLoaded", async () => {
  const page = document.body.dataset.page;
  if (!page) return;

  if (DEMO) {
    TOKEN = "demo";
  } else if (tg?.initData) {
    try {
      const r = await fetch(API + "/miniapp/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ init_data: tg.initData }),
      });
      if (!r.ok) throw new Error("auth " + r.status);
      TOKEN = (await r.json()).token;
    } catch {
      showGate("احراز هویت ناموفق بود. لطفاً از داخل بات دوباره بازش کن.");
      return;
    }
  } else {
    showGate("این صفحه فقط از داخل بات تلگرام باز می‌شه.");
    return;
  }

  if (page === "library") initLibrary();
  if (page === "viewer") initViewer();
});

function showGate(msg) {
  document.getElementById("app").innerHTML = `<div class="center-msg">${msg}</div>`;
}

/* ── کتابخانه (خریدهای من) ────────── */

async function initLibrary() {
  const root = document.getElementById("app");
  const head =
    `<h2 class="lib-head">کتابخانه‌ی من</h2>` +
    `<div class="lib-sub">جزوه‌هایی که خریدی — برای مطالعه‌ی آنلاین</div>`;
  if (DEMO) {
    root.innerHTML = head + DEMO_DB.notes.slice(0, 3).map(libItemHtml).join("");
    return;
  }
  try {
    const r = await fetch(`${API}/miniapp/purchases?token=${encodeURIComponent(TOKEN)}`);
    if (!r.ok) throw new Error();
    const items = (await r.json()).items;
    root.innerHTML =
      head +
      (items.length
        ? items.map(libItemHtml).join("")
        : '<div class="empty">هنوز جزوه‌ای نخریدی — از داخل بات اولین جزوه‌ت رو بخر.</div>');
  } catch {
    root.innerHTML = '<div class="error-box">خطا در بارگذاری کتابخانه.</div>';
  }
}

function libItemHtml(n) {
  const letter = esc((n.title || "ج").trim().charAt(0));
  return `
    <div class="lib-item">
      <div class="cover">${letter}</div>
      <div>
        <h3>${esc(n.title)}</h3>
        <div class="meta">${esc(n.course)} ← ${esc(n.professor)}</div>
      </div>
      <a class="btn" href="viewer.html?note=${n.id}">مطالعه</a>
    </div>`;
}

/* ── خواننده ──────────────────────── */

async function initViewer() {
  const root = document.getElementById("app");
  // در حالت دمو بدون پارامتر هم جزوه نمایشی ۱ نشون داده می‌شه
  const noteId = new URLSearchParams(location.search).get("note") || (DEMO ? "1" : null);
  if (!noteId) {
    root.innerHTML = '<div class="error-box">جزوه مشخص نشده.</div>';
    return;
  }

  // جلوگیری از راست‌کلیک و ذخیره (سرعت‌گیر)
  document.addEventListener("contextmenu", (e) => e.preventDefault());

  let pageCount = 0;
  let title = "جزوه";
  if (DEMO) {
    pageCount = 5;
    title = "ساختمان داده — جمع‌بندی کامل";
  } else {
    try {
      const r = await fetch(
        `${API}/miniapp/notes/${noteId}/pages?token=${encodeURIComponent(TOKEN)}`
      );
      if (!r.ok) throw new Error();
      const d = await r.json();
      pageCount = d.page_count;
      title = d.title || title;
    } catch {
      root.innerHTML =
        '<div class="error-box">دسترسی نداری یا جزوه پیدا نشد.<br>اول از داخل بات بخرش.</div>';
      return;
    }
  }

  root.innerHTML = `
    <div class="vbar">
      <a href="library.html">‹ کتابخانه</a>
      <span class="title">${esc(title)}</span>
      <span class="count" id="page-indicator">۱ / ${faNum(pageCount)}</span>
    </div>
    <div class="viewer" id="pages"></div>
    <div class="wm-note">این نسخه مخصوص توئه — روی هر صفحه واترمارک شخصی حک شده و انتشارش قابل ردیابیه.</div>`;

  const pagesBox = document.getElementById("pages");
  const pageSrc = (i) =>
    DEMO
      ? demoPreviewUrl(i, title)
      : `${API}/miniapp/notes/${noteId}/pages/${i}?token=${encodeURIComponent(TOKEN)}`;

  // بارگذاری تنبل صفحه‌به‌صفحه
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      const img = en.target;
      if (en.isIntersecting && img.dataset.src) {
        img.src = img.dataset.src;
        delete img.dataset.src;
      }
      if (en.isIntersecting) {
        const ind = document.getElementById("page-indicator");
        if (ind) ind.textContent = `${faNum(img.dataset.page)} / ${faNum(pageCount)}`;
      }
    });
  }, { rootMargin: "400px" });

  for (let i = 1; i <= pageCount; i++) {
    const frame = document.createElement("div");
    frame.className = "doc-frame";
    const img = document.createElement("img");
    img.dataset.src = pageSrc(i);
    img.dataset.page = i;
    img.alt = `صفحه ${faNum(i)}`;
    img.draggable = false;
    img.height = 880;
    frame.appendChild(img);
    observer.observe(img);
    pagesBox.appendChild(frame);
  }
}
