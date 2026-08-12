/* حساب کاربری مستقل — ورود/ثبت‌نام با ایمیل + مشاهده کیف پول و خریدها
   احراز با Bearer token در localStorage — مستقل از تلگرام. */

const TOKEN_KEY = "nb_token";
const getToken = () => localStorage.getItem(TOKEN_KEY);
const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
const clearToken = () => localStorage.removeItem(TOKEN_KEY);

async function authApi(path, body, withAuth = false) {
  if (DEMO) return demoAuth(path, body, withAuth);
  const headers = { "Content-Type": "application/json" };
  if (withAuth && getToken()) headers["Authorization"] = "Bearer " + getToken();
  const r = await fetch(API + path, {
    method: body ? "POST" : "GET",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "خطا");
  return data;
}

/* ── حالت دمو (file:// یا ?demo=1) ── */
function demoAuth(path, body, withAuth) {
  if (path === "/auth/me")
    return { id: 1, name: "کاربر نمایشی", email: "demo@notebazar.ir", telegram_linked: false, is_admin: false, balance: 85000 };
  if (path === "/purchases/mine")
    return { items: DEMO_DB.notes.slice(0, 2).map((n) => ({ id: n.id, note_id: n.id, title: n.title, price_toman: n.price_toman })) };
  if (path === "/auth/login" || path === "/auth/register")
    return { token: "demo", name: body?.name || "کاربر نمایشی" };
  return {};
}

document.addEventListener("DOMContentLoaded", () => {
  if (getToken()) showAccount();
  else showAuth();
});

/* ── فرم ورود / ثبت‌نام ────────────── */

function showAuth() {
  document.getElementById("app").innerHTML = `
    <div class="auth-card">
      <h1>حساب کاربری</h1>
      <div class="tabs">
        <button id="tab-login" class="active">ورود</button>
        <button id="tab-register">ثبت‌نام</button>
      </div>
      <div class="alert" id="alert"></div>
      <form id="auth-form">
        <div class="field" id="name-field" style="display:none">
          <label>نام</label>
          <input type="text" id="f-name" autocomplete="name">
        </div>
        <div class="field">
          <label>ایمیل</label>
          <input type="email" id="f-email" dir="ltr" autocomplete="email" required>
        </div>
        <div class="field">
          <label>رمز عبور</label>
          <input type="password" id="f-pass" dir="ltr" autocomplete="current-password" required>
        </div>
        <button class="btn btn-primary btn-block" type="submit" id="submit-btn">ورود</button>
      </form>
      <p class="hint">اکانت مستقل از تلگرامه — خریدها و کیف پولت اینجا هم هست.</p>
    </div>`;

  let mode = "login";
  const alertBox = document.getElementById("alert");
  const showError = (msg) => {
    alertBox.textContent = msg;
    alertBox.classList.add("show");
  };

  const setMode = (m) => {
    mode = m;
    document.getElementById("tab-login").classList.toggle("active", m === "login");
    document.getElementById("tab-register").classList.toggle("active", m === "register");
    document.getElementById("name-field").style.display = m === "register" ? "block" : "none";
    document.getElementById("submit-btn").textContent = m === "register" ? "ثبت‌نام" : "ورود";
    alertBox.classList.remove("show");
  };
  document.getElementById("tab-login").onclick = () => setMode("login");
  document.getElementById("tab-register").onclick = () => setMode("register");

  document.getElementById("auth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("f-email").value.trim();
    const password = document.getElementById("f-pass").value;
    const name = document.getElementById("f-name").value.trim();
    try {
      const data =
        mode === "register"
          ? await authApi("/auth/register", { email, password, name })
          : await authApi("/auth/login", { email, password });
      setToken(data.token);
      showAccount();
    } catch (err) {
      showError(err.message || "خطایی پیش اومد");
    }
  });
}

/* ── نمای حساب ─────────────────────── */

async function showAccount() {
  const app = document.getElementById("app");
  app.style.maxWidth = "640px";
  let me;
  try {
    me = await authApi("/auth/me", null, true);
  } catch {
    clearToken();
    app.style.maxWidth = "";
    showAuth();
    return;
  }

  let purchasesHtml = '<div class="empty">هنوز خریدی نداری.</div>';
  try {
    const p = await authApi("/purchases/mine", null, true);
    if (p.items.length) {
      purchasesHtml =
        '<div class="catalog">' +
        p.items
          .map(
            (it, i) => `
          <article class="nrow">
            <span class="nrow-idx">${faNum(String(i + 1).padStart(2, "0"))}</span>
            <div class="nrow-main">
              <h3><a href="note.html?id=${it.note_id}">${esc(it.title)}</a></h3>
            </div>
            <div class="nrow-side">
              <div class="nrow-price">${faNum(it.price_toman)}<small>تومان</small></div>
            </div>
          </article>`
          )
          .join("") +
        "</div>";
    }
  } catch {}

  app.innerHTML = `
    <div class="acct-head">
      <h1>${esc(me.name || "کاربر")}</h1>
      <p>${esc(me.email || "")}${me.telegram_linked ? " · متصل به تلگرام" : ""}</p>
    </div>
    <div class="acct-actions">
      <span class="btn" style="cursor:default">💰 موجودی: <b>${faNum(me.balance)} تومان</b></span>
      <button class="btn" id="logout-btn">خروج</button>
    </div>
    <h2 class="block-title">خریدهای من</h2>
    ${purchasesHtml}`;

  document.getElementById("logout-btn").onclick = () => {
    clearToken();
    location.reload();
  };
}
