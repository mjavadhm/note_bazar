# NoteBazar 🎓 — جزوه‌بازار

بات تلگرام + سایت + مینی‌اپ برای خرید و فروش جزوه دانشجویی — با کیف پول داخلی،
**اکانت مستقل از تلگرام (ایمیل/رمز)**، پیش‌نمایش واترمارک‌دار، خواننده آنلاین با
واترمارک شخصی، و **ایمپورت مستقیم خروجی کراولر tgarchive** (JSON دسته‌ای، CSV اکسپورت،
یا تک‌فایل) با نوع مدرک، ترم و تگ.

## معماری

```
Telegram User ──▶ bot (aiogram) ──┐
Browser ────────▶ web (nginx) ────┤   احراز دومسیره:
Telegram MiniApp (viewer) ────────┤   • تلگرام: X-Bot-Secret + X-Telegram-Id
Crawler ────────▶ /import/* ──────┤   • مستقل: Bearer token (ایمیل/رمز)
                                  v
                            api (FastAPI)
                                  |
        +-------------------------+-------------------------+
        v                         v                         v
   postgres 16            redis (FSM + Celery)         minio (S3)
                                                           ^
                                                      worker (Celery)
                                                      preview builder
```

## راه‌اندازی (۳ قدم)

```bash
cp .env.example .env   # BOT_TOKEN + ADMIN_TELEGRAM_IDS + API_SECRET
docker compose up --build -d
docker compose logs -f bot
```

## 🔌 پورت‌ها (بلاک متوالی 8310 تا 8312)

| پورت | سرویس | چیه |
|---|---|---|
| **8310** | `web` | 🌐 سایت + مینی‌اپ |
| **8311** | `api` | ⚙️ API — مستندات: `http://SERVER:8311/docs` |
| **8312** | `minio` | 🗄️ کنسول فایل‌ها (minio / minio123) |

- پورت‌ها روی `0.0.0.0` باز می‌شن → `http://IP-SERVER:8310`
- فایروال: `sudo ufw allow 8310:8312/tcp`

## 👤 اکانت مستقل از تلگرام

مدل `User` دیگر به تلگرام وابسته نیست — هر کاربر می‌تونه `telegram_id`،
`email`+`password_hash`، یا هر دو رو داشته باشه:

- **بات:** ثبت‌نام خودکار با `/start` (تلگرام یک provider هست، نه تنها راه)
- **سایت:** صفحه `account.html` ← ثبت‌نام/ورود با ایمیل و رمز ← توکن Bearer
  (stateless، امضاشده با API_SECRET، یک‌ماهه)
- همه اندپوینت‌های کاربری هر دو مسیر احراز رو قبول می‌کنن

## 📚 فیلدهای جزوه (هم‌راستا با کراولر tgarchive)

| فیلد | مثال | توضیح |
|---|---|---|
| `kind` | «نمونه سوال پایانترم» | واژگان کنترل‌شده — دقیقاً مثل `doc_type` کراولر |
| `term` | «4041» | خام — مثل خروجی کراولر |
| `term_display` | «بهار ۱۴۰۴» | مشتق خودکار (۴۰۴۱ ← سال ۱۴۰۴، نیمسال ۱=بهار) |
| `tags` | ["جمع‌بندی", "حل تمرین"] | حداکثر ۱۰ |

فیلترها: `?kind=` / `?term=` / `?tag=` + جستجوی متنی روی عنوان، توضیح، نوع و تگ‌ها.

## 🕷️ ایمپورت از کراولر

### الف) CSV خروجی `/export` کراولر — ساده‌ترین راه

توی کراولر (باتش یا ترمینال) خروجی بگیر:

```bash
# توی بات tgarchive (ادمین):  /export
# یا ترمینال:
python -m tools.manage export out.csv
```

بعد آپلودش کن:

```bash
curl -X POST http://localhost:8311/import/csv \
  -H "X-Bot-Secret: $API_SECRET" -H "X-Telegram-Id: $ADMIN_TG_ID" \
  -F "default_price=30000" \
  -F "file=@out.csv"
```

- فقط ردیف‌های `status=ready` وارد می‌شن
- ردیف‌های **متنی** (`media_type=text` با body) کامل وارد می‌شن → فایل `.txt`
- ردیف‌های **رسانه‌ای** (pdf/photo/document) فایل ندارن (file_id مال بات کراولره)
  → توی خروجی با خطای مشخص گزارش می‌شن تا با راه (ج) آپلودشون کنی
- CSV قیمت نداره → `default_price` روی همه اعمال می‌شه
- ستون `tags` توی CSV به صورت JSON array هست — خودکار پارس می‌شه

جواب: `{"imported": n, "failed": m, "skipped": k, "results": [...]}`

### ب) دسته‌ای JSON — `POST /import/crawl`

دقیقاً با خروجی enricher (تا ۱۰۰ آیتم در درخواست):

```bash
curl -X POST http://localhost:8311/import/crawl \
  -H "X-Bot-Secret: $API_SECRET" -H "X-Telegram-Id: $ADMIN_TG_ID" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"university":"دانشگاه صنعتی شریف","course_name":"ریاضی 1",
    "professor":"احمدی","term":"4041","doc_type":"نمونه سوال پایانترم",
    "tags":["نمونه سوال"],"price_toman":30000,"media_type":"text","body":"..."}]}'
```

### ج) تک‌فایل multipart — `POST /import/notes`

```bash
curl -X POST http://localhost:8311/import/notes \
  -H "X-Bot-Secret: $API_SECRET" -H "X-Telegram-Id: $ADMIN_TG_ID" \
  -F "university=دانشگاه صنعتی شریف" -F "course=ریاضی ۱" -F "professor=احمدی" \
  -F "title=ریاضی ۱ — نمونه سوال" -F "kind=نمونه سوال پایانترم" -F "term=4041" \
  -F "tags=نمونه سوال" -F "price_toman=30000" -F "file=@notes.pdf"
```

- درخت دانشگاه ← درس ← استاد خودکار find-or-create و تأیید می‌شه (دانشکده: «سایر»)
- استاد خالی ← «نامشخص» · عنوان خالی ← خودکار از نوع+درس+استاد+ترم
- ⚠️ `telegram_file_id` باید متعلق به بات نوت‌بازار باشه (file_id بات کراولر معتبر نیست)

## تست فلو

۱. `/start` توی بات ← ثبت‌نام خودکار
۲. «💰 کیف پول» ← «شارژ تستی» (ادمین)
۳. «➕ فروش جزوه» ← فایل ← عنوان ← توضیح ← قیمت ← ترم ← تگ‌ها ← نوع مدرک ← درخت
۴. `/panel` ← تأیید جزوه و پیشنهادها
۵. «🔍 جستجو» ← «👁 پیش‌نمایش» ← «🛒 خرید» ← فایل + امتیاز

## تصمیم‌های طراحی

- **احراز:** دومسیره (بات با سکرت مشترک / Bearer token برای اکانت مستقل) — stateless.
- **کیف پول:** Ledger غیرقابل‌تغییر؛ موجودی محاسبه‌ای. درگاه واقعی فعلاً نیومده.
- **خرید:** آزادسازی فوری + کمیسیون. قلاب escrow: `Purchase.status`.
- **ضد کپی:** پیش‌نمایش واترمارک‌دار + خواننده مینی‌اپ با واترمارک شخصی خریدار.
- **متادیتا:** `kind` با واژگان کنترل‌شده (هم‌راستا با کراولر) + `term` خام + `term_display` مشتق.
- **اسکیما:** `create_all` — بعد از تغییر مدل‌ها: `docker compose down -v && docker compose up --build -d`.

## گام‌های بعدی

- [ ] Alembic برای migration
- [ ] درگاه پرداخت (زرین‌پال) + تسویه فروشنده
- [ ] خرید مستقیم از سایت با اکانت ایمیلی
- [ ] اتصال اکانت تلگرام به ایمیل (ادغام کیف پول‌ها)
- [ ] `delivery_mode` روی جزوه (فقط آنلاین / دانلود واترمارک‌دار / آزاد)
- [ ] escrow با Celery beat + گزارش تخلف + refund

## ساختار پوشه‌ها

```
notebazar/
├── docker-compose.yml      # پورت‌ها: 8310 وب، 8311 ایپی‌آی، 8312 مینیو
├── .env.example
├── api/              # FastAPI
│   └── app/
│       ├── routers/           # auth, taxonomy, notes, purchases, wallet, admin, public, miniapp, importer
│       ├── normalize.py       # DOC_TYPES + doc_type() + parse_term/term_display
│       ├── tokens.py          # توکن نشست stateless برای اکانت مستقل
│       ├── deps.py            # احراز دومسیره (بات / Bearer)
│       ├── miniapp_security.py# اعتبارسنجی initData تلگرام
│       └── personal_render.py # رندر صفحه با واترمارک شخصی
├── bot/              # aiogram 3 — فلوی فروش: فایل ← عنوان ← توضیح ← قیمت ← ترم ← تگ ← نوع ← درخت
├── worker/           # Celery — پیش‌نمایش واترمارک‌دار PDF
└── web/              # سایت + مینی‌اپ (vanilla JS)
    ├── index.html / note.html / account.html / library.html / viewer.html
    ├── config.js              # ⚙️ یوزرنیم بات
    ├── nginx.conf             # پروکسی /api
    └── assets/                # styles.css, app.js, site.js, miniapp.js, account.js
```
