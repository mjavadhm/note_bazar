/* منطق صفحات سایت (index + note) */

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page === "home") initHome();
  if (page === "note") initNote();
});

function botLink(startParam) {
  const user = window.NB_CONFIG?.botUsername || "YOUR_BOT_USERNAME";
  return "https://t.me/" + user + (startParam ? "?start=" + startParam : "");
}

/* ── صفحه اصلی ────────────────────── */

async function initHome() {
  document.querySelectorAll("[data-bot-link]").forEach((a) => (a.href = botLink()));

  try {
    const s = await api("/public/stats");
    setText("stat-notes", faNum(s.notes));
    setText("stat-unis", faNum(s.universities));
    setText("stat-buys", faNum(s.purchases));
  } catch {}

  const selUni = document.getElementById("f-uni");
  const selFac = document.getElementById("f-fac");
  const selCourse = document.getElementById("f-course");
  const selProf = document.getElementById("f-prof");

  const fill = (sel, items) => {
    sel.innerHTML =
      `<option value="">همه</option>` +
      items.map((i) => `<option value="${i.id}">${esc(i.name)}</option>`).join("");
  };

  try {
    fill(selUni, await api("/public/taxonomy/universities"));
  } catch {}

  selUni.addEventListener("change", async () => {
    fill(selFac, []);
    fill(selProf, []);
    if (selUni.value) {
      fill(selFac, await api(`/public/taxonomy/faculties?university_id=${selUni.value}`));
      fill(selProf, await api(`/public/taxonomy/professors?university_id=${selUni.value}`));
    }
    loadNotes();
  });
  selFac.addEventListener("change", async () => {
    fill(selCourse, []);
    if (selFac.value)
      fill(selCourse, await api(`/public/taxonomy/courses?faculty_id=${selFac.value}`));
    loadNotes();
  });
  selCourse.addEventListener("change", loadNotes);
  selProf.addEventListener("change", loadNotes);

  document.getElementById("search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    loadNotes();
    document.getElementById("catalog").scrollIntoView({ behavior: "smooth" });
  });

  loadNotes();

  async function loadNotes() {
    const box = document.getElementById("notes-grid");
    box.innerHTML = '<p class="center-msg">در حال بارگذاری…</p>';
    const params = new URLSearchParams();
    const q = document.getElementById("search-input").value.trim();
    if (q) params.set("q", q);
    if (selUni.value) params.set("university_id", selUni.value);
    if (selFac.value) params.set("faculty_id", selFac.value);
    if (selCourse.value) params.set("course_id", selCourse.value);
    if (selProf.value) params.set("professor_id", selProf.value);
    params.set("limit", "24");
    try {
      const data = await api("/public/notes?" + params);
      setText("notes-count", "— " + faNum(data.total) + " مورد");
      box.innerHTML = data.items.length
        ? data.items.map((n, i) => noteCardHtml(n, i + 1)).join("")
        : '<div class="empty">جزوه‌ای با این مشخصات پیدا نشد.<br>فیلترها رو عوض کن یا جستجو رو دقیق‌تر بنویس.</div>';
    } catch {
      box.innerHTML = '<div class="error-box">ارتباط با سرور برقرار نشد.<br>چند لحظه دیگه تلاش کن.</div>';
    }
  }
}

/* ── صفحه جزوه ────────────────────── */

async function initNote() {
  // NB_DEMO_NOTE_ID فقط برای پیش‌نمایش/تست بدون کوئری‌استرینگه
  const id = new URLSearchParams(location.search).get("id") || window.NB_DEMO_NOTE_ID;
  const root = document.getElementById("note-root");
  if (!id) {
    root.innerHTML = '<div class="error-box">جزوه مشخص نشده.</div>';
    return;
  }
  try {
    const n = await api(`/public/notes/${id}`);
    document.title = n.title + " — جزوه‌بازار";

    const termText = n.term_display || n.term;

    root.innerHTML = `
      <div class="doc-head">
        <div class="breadcrumb">${esc(n.university)} ← ${esc(n.faculty)} ← ${esc(n.course)}</div>
        <h1>${esc(n.title)}</h1>
        ${n.tags?.length ? `<div class="tags">${tagsLine(n.tags)}</div>` : ""}
        <div>${starsHtml(n.rating_avg, n.rating_count)}</div>
      </div>
      <div class="detail">
        <aside class="info-panel">
          ${n.kind ? `<div class="kv"><span>نوع مدرک</span><b>${esc(n.kind)}</b></div>` : ""}
          <div class="kv"><span>استاد</span><b>${esc(n.professor)}</b></div>
          <div class="kv"><span>حجم</span><b>${n.page_count ? faNum(n.page_count) + " صفحه" : esc(n.file_name)}</b></div>
          ${termText ? `<div class="kv"><span>ترم</span><b>${esc(termText)}</b></div>` : ""}
          <div class="kv"><span>فروشنده</span><b>${esc(n.seller_name)}</b></div>
          <div class="big-price">${n.price_toman === 0 ? "رایگان" : faNum(n.price_toman) + " <small>تومان</small>"}</div>
          <a class="btn btn-primary btn-lg btn-block" href="${botLink("note_" + n.id)}" target="_blank" rel="noopener">
            خرید در تلگرام
          </a>
          <div class="secure-note">پرداخت و دریافت فایل داخل بات تلگرام انجام می‌شه</div>
        </aside>
        <div>
          <section class="preview-list"><h2 class="block-title">پیش‌نمایش واترمارک‌دار</h2><div id="previews"></div></section>
          ${n.description ? `<section style="margin-top:32px"><h2 class="block-title">توضیحات فروشنده</h2><p class="desc-text">${esc(n.description)}</p></section>` : ""}
          <section class="reviews" style="margin-top:32px" id="reviews-section"><h2 class="block-title">نظر خریدارها</h2><div id="reviews"></div></section>
        </div>
      </div>`;

    try {
      const pv = await api(`/public/notes/${id}/preview`);
      document.getElementById("previews").innerHTML = pv.urls.length
        ? pv.urls.map((u) => `<div class="doc-frame"><img src="${u}" alt="پیش‌نمایش" loading="lazy"></div>`).join("")
        : '<div class="empty">این جزوه پیش‌نمایش نداره.</div>';
    } catch {
      document.getElementById("previews").innerHTML = '<div class="empty">پیش‌نمایش در دسترس نیست.</div>';
    }

    try {
      const rv = await api(`/public/notes/${id}/reviews`);
      document.getElementById("reviews").innerHTML = rv.items.length
        ? rv.items
            .map(
              (r) => `<div class="review">
                <div class="stars">${"★".repeat(r.rating)}${"☆".repeat(5 - r.rating)}</div>
                ${r.comment ? `<p>${esc(r.comment)}</p>` : ""}
                <div class="who">${esc(r.buyer)}</div>
              </div>`
            )
            .join("")
        : '<div class="empty">هنوز نظری ثبت نشده.</div>';
    } catch {
      document.getElementById("reviews-section").style.display = "none";
    }
  } catch {
    root.innerHTML = '<div class="error-box">جزوه پیدا نشد یا ارتباط برقرار نشد.</div>';
  }
}

function setText(id, t) {
  const el = document.getElementById(id);
  if (el) el.textContent = t;
}
