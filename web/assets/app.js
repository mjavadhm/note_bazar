/* توابع مشترک سایت و مینی‌اپ */

const API = "/api";

// حالت دمو: با ?demo=1 یا اجرا از روی فایل (بدون بک‌اند) داده نمایشی نشون میده
const DEMO =
  new URLSearchParams(location.search).has("demo") ||
  location.protocol === "file:";

const faNum = (n) => Number(n).toLocaleString("fa-IR");

const moneyText = (t) => (t === 0 ? "رایگان" : faNum(t) + " تومان");

function starsHtml(avg, count) {
  if (!count) return '<span class="stars"><span class="n">بدون امتیاز</span></span>';
  const full = Math.round(avg);
  return `<span class="stars">${"★".repeat(full)}${"☆".repeat(5 - full)} <span class="n">${avg} (${faNum(count)})</span></span>`;
}

function tagsLine(tags) {
  return (tags || []).map((t) => `<span>#${esc(t)}</span>`).join("");
}

/* ردیف کاتالوگ — فهرست تحریریه با شماره ردیف */
function noteCardHtml(n, idx) {
  const no = String(idx ?? "").padStart(2, "0");
  const sub = [
    n.kind ? esc(n.kind) : null,
    n.rating_count ? `<span class="amber">★ ${n.rating_avg} (${faNum(n.rating_count)})</span>` : null,
    n.page_count ? `${faNum(n.page_count)} صفحه` : null,
    n.term_display || n.term ? esc(n.term_display || n.term) : null,
    n.has_preview ? "پیش‌نمایش دارد" : null,
  ].filter(Boolean).join(" · ");
  return `
    <article class="nrow">
      <span class="nrow-idx">${faNum(no)}</span>
      <div class="nrow-main">
        <h3><a href="note.html?id=${n.id}">${esc(n.title)}</a></h3>
        <div class="nrow-meta">${esc(n.university)} · ${esc(n.course)} · ${esc(n.professor)}</div>
        ${sub ? `<div class="nrow-sub">${sub}</div>` : ""}
        ${n.tags?.length ? `<div class="nrow-tags">${tagsLine(n.tags)}</div>` : ""}
      </div>
      <div class="nrow-side">
        <div class="nrow-price ${n.price_toman === 0 ? "free" : ""}">${n.price_toman === 0 ? "رایگان" : faNum(n.price_toman) + "<small>تومان</small>"}</div>
        <a class="btn-mini" href="note.html?id=${n.id}">مشاهده ←</a>
      </div>
    </article>`;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function api(path) {
  if (DEMO) return demoRoute(path);
  const r = await fetch(API + path);
  if (!r.ok) throw new Error("API " + r.status);
  return r.json();
}

/* ── داده دمو ─────────────────────── */

const DEMO_DB = {
  universities: [
    { id: 1, name: "دانشگاه صنعتی شریف" },
    { id: 2, name: "دانشگاه تهران" },
    { id: 3, name: "دانشگاه امیرکبیر" },
  ],
  faculties: [
    { id: 1, name: "مهندسی کامپیوتر", university_id: 1 },
    { id: 2, name: "ریاضی", university_id: 1 },
    { id: 3, name: "مهندسی برق", university_id: 2 },
  ],
  courses: [
    { id: 1, name: "ساختمان داده", faculty_id: 1, university_id: 1 },
    { id: 2, name: "ریاضی ۱", faculty_id: 2, university_id: 1 },
    { id: 3, name: "مدار منطقی", faculty_id: 3, university_id: 2 },
  ],
  professors: [
    { id: 1, name: "دکتر احمدی", university_id: 1 },
    { id: 2, name: "دکتر رضایی", university_id: 1 },
    { id: 3, name: "دکتر کریمی", university_id: 2 },
  ],
  notes: [
    { id: 1, title: "ساختمان داده — جمع‌بندی کامل با تمرین حل‌شده", description: "خلاصه‌ی دست‌نویس همه فصل‌ها به‌همراه تمرین‌های امتحانی سه ترم اخیر.", price_toman: 45000, page_count: 68, kind: "جزوه", term: "4041", term_display: "بهار ۱۴۰۴", tags: ["جمع‌بندی", "حل تمرین"], rating_avg: 4.6, rating_count: 23, has_preview: true, university: "دانشگاه صنعتی شریف", faculty: "مهندسی کامپیوتر", course: "ساختمان داده", professor: "دکتر احمدی", seller_name: "سارا", file_name: "data-structures.pdf" },
    { id: 2, title: "ریاضی ۱ — فصل ۱ تا ۴ (حد، مشتق، پیوستگی)", description: "جزوه تایپ‌شده با مثال‌های تشریحی و نکات امتحانی.", price_toman: 30000, page_count: 42, kind: "جزوه", term: "4032", term_display: "پاییز ۱۴۰۳", tags: ["تایپ‌شده", "نکات امتحانی"], rating_avg: 4.2, rating_count: 11, has_preview: true, university: "دانشگاه صنعتی شریف", faculty: "ریاضی", course: "ریاضی ۱", professor: "دکتر رضایی", seller_name: "علی", file_name: "math1.pdf" },
    { id: 3, title: "مدار منطقی — اسلایدهای حاشیه‌نویسی‌شده", description: "اسلایدهای استاد با توضیحات کلاس، خط‌به‌خط.", price_toman: 25000, page_count: 120, kind: "اسلاید", term: "4041", term_display: "بهار ۱۴۰۴", tags: ["اسلاید", "کلاس"], rating_avg: 4.8, rating_count: 31, has_preview: true, university: "دانشگاه تهران", faculty: "مهندسی برق", course: "مدار منطقی", professor: "دکتر کریمی", seller_name: "مریم", file_name: "logic.pdf" },
    { id: 4, title: "ساختمان داده — کدهای آماده پایتون", description: "پیاده‌سازی همه ساختمان‌داده‌ها با تست.", price_toman: 0, page_count: 25, kind: "پروژه", term: "4042", term_display: "پاییز ۱۴۰۴", tags: ["کد", "پایتون"], rating_avg: 4.0, rating_count: 8, has_preview: false, university: "دانشگاه صنعتی شریف", faculty: "مهندسی کامپیوتر", course: "ساختمان داده", professor: "دکتر احمدی", seller_name: "رضا", file_name: "ds-code.pdf" },
    { id: 5, title: "ریاضی ۱ — نمونه سوال ۱۰ ترم اخیر با پاسخ", description: "آرشیو کامل نمونه سوالات با پاسخ تشریحی.", price_toman: 55000, page_count: 95, kind: "نمونه سوال پایانترم", term: "4041", term_display: "بهار ۱۴۰۴", tags: ["نمونه سوال", "پاسخ تشریحی"], rating_avg: 4.9, rating_count: 47, has_preview: true, university: "دانشگاه صنعتی شریف", faculty: "ریاضی", course: "ریاضی ۱", professor: "دکتر رضایی", seller_name: "نگار", file_name: "math1-exams.pdf" },
    { id: 6, title: "مدار منطقی — جمع‌بندی شبکه‌های ترکیبی و ترتیبی", description: "فقط نکته و فرمول — مخصوص شب امتحان.", price_toman: 20000, page_count: 18, kind: "خلاصه", term: "4042", term_display: "پاییز ۱۴۰۴", tags: ["جمع‌بندی", "شب امتحان"], rating_avg: 3.9, rating_count: 6, has_preview: true, university: "دانشگاه تهران", faculty: "مهندسی برق", course: "مدار منطقی", professor: "دکتر کریمی", seller_name: "حسین", file_name: "logic-summary.pdf" },
  ],
  reviews: [
    { rating: 5, comment: "دقیقاً همون چیزی بود که لازم داشتم، تمرین‌ها عالی بودن 👌", buyer: "امیر" },
    { rating: 4, comment: "خوب و مرتب، کاش فصل پنجم هم بود.", buyer: "زهرا" },
  ],
};

function demoPreviewUrl(page, title) {
  const lines = Array.from({ length: 14 }, (_, i) =>
    `<rect x='60' y='${150 + i * 42}' width='${420 - (i % 3) * 90}' height='12' rx='6' fill='#D9D8D5'/>`
  ).join("");
  const svg =
    `<svg xmlns='http://www.w3.org/2000/svg' width='640' height='880'>` +
    `<rect width='640' height='880' fill='#FFFFFF'/>` +
    `<rect x='60' y='70' width='360' height='22' rx='8' fill='#B9B7B2'/>` +
    lines +
    `<text x='320' y='440' font-size='34' fill='rgba(220,30,30,0.25)' transform='rotate(-30 320 440)' text-anchor='middle'>NOTEBAZAR PREVIEW</text>` +
    `<text x='320' y='850' font-size='16' fill='#9B9A97' text-anchor='middle'>صفحه ${page} — ${title}</text>` +
    `</svg>`;
  return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
}

function demoRoute(path) {
  const [p, qs] = path.split("?");
  const params = new URLSearchParams(qs || "");
  const q = (params.get("q") || "").trim();

  if (p === "/public/stats")
    return { notes: 342, universities: 12, purchases: 1840 };
  if (p === "/public/taxonomy/universities") return DEMO_DB.universities;
  if (p === "/public/taxonomy/faculties")
    return DEMO_DB.faculties.filter((f) => f.university_id == params.get("university_id"));
  if (p === "/public/taxonomy/courses")
    return DEMO_DB.courses.filter((c) => c.faculty_id == params.get("faculty_id"));
  if (p === "/public/taxonomy/professors")
    return DEMO_DB.professors.filter((x) => x.university_id == params.get("university_id"));
  if (p === "/public/notes") {
    let items = DEMO_DB.notes;
    if (q)
      items = items.filter((n) =>
        (n.title + n.course + n.professor + (n.kind || "") + (n.tags || []).join(" ")).includes(q)
      );
    if (params.get("university_id"))
      items = items.filter((n) => n.university === DEMO_DB.universities.find((u) => u.id == params.get("university_id"))?.name);
    if (params.get("tag"))
      items = items.filter((n) => (n.tags || []).includes(params.get("tag")));
    if (params.get("term"))
      items = items.filter((n) => n.term === params.get("term"));
    if (params.get("kind"))
      items = items.filter((n) => n.kind === params.get("kind"));
    return { total: items.length, items };
  }
  let m = p.match(/^\/public\/notes\/(\d+)$/);
  if (m) {
    const n = DEMO_DB.notes.find((x) => x.id == m[1]);
    if (!n) throw new Error("not found");
    return n;
  }
  m = p.match(/^\/public\/notes\/(\d+)\/preview$/);
  if (m) {
    const n = DEMO_DB.notes.find((x) => x.id == m[1]);
    return { urls: n?.has_preview ? [1, 2, 3].map((i) => demoPreviewUrl(i, n.title)) : [] };
  }
  m = p.match(/^\/public\/notes\/(\d+)\/reviews$/);
  if (m) return { items: DEMO_DB.reviews };
  throw new Error("demo: unknown route " + path);
}
