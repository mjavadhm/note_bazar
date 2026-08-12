# NoteBazar 🎓 — جزوه‌بازار

بات تلگرام + سایت + مینی‌اپ برای خرید و فروش جزوه دانشجویی — با کیف پول داخلی،
**اکانت مستقل از تلگرام (ایمیل/رمز)**، پیش‌نمایش واترمارک‌دار، خواننده آنلاین با
واترمارک شخصی، و **ایمپورت مستقیم خروجی کراولر tgarchive** (نوع مدرک، ترم، تگ).

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
  (stateless، امضاشده با API_SECRET، یک‌ماهه) — کیف پول و خریدها اونجا هم هستن
- همه اندپوینت‌های کاربری هر دو مسیر احراز رو قبول می‌کنن

```bash
# نمونه: ثبت‌نام و گرفتن موجودی با توکن
curl -X POST http://localhost:8311/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"a@b.com","password":"secret1","name":"علی"}'
curl http://localhost:8311/auth/me -H "Authorization: Bearer <TOKEN>"
```

## 📚 فیلدهای جزوه (هم‌راستا با کراولر tgarchive)

| فیلد | مثال | توضیح |
|---|---|---|
| `kind` | «نمونه سوال پایانترم» | واژگان کنترل‌شده — دقیقاً مثل `doc_type` کراولر |
| `term` | «4041» | خام — مثل خروجی کراولر |
| `term_display` | «بهار ۱۴۰۴» | مشتق خودکار برای نمایش (۴۰۴۱ ← سال ۱۴۰۴، نیمسال ۱=بهار) |
| `tags` | ["جمع‌بندی", "حل تمرین"] | حداکثر ۱۰ |

فیلترها: `GET /notes?kind=...&term=4041&tag=...` و `GET /public/notes?...`
(جستجوی متنی روی عنوان، توضیح، نوع مدرک و تگ‌ها هم کار می‌کنه).

## 🕷️ ایمپورت از کراولر

### دسته‌ای — دقیقاً با خروجی enricher

```bash
curl -X POST http://localhost:8311/import/crawl \
  -H "X-Bot-Secret: $API_SECRET" -H "X-Telegram-Id: $ADMIN_TG_ID" \
  -H "Content-Type: application/json" \
  -d '{"items": [{
    "university": "دانشگاه صنعتی شریف",
    "course_name": "ریاضی 1",
    "professor": "احمدی",
    "term": "4041",
    "doc_type": "نمونه سوال پایانترم",
    "tags": ["نمونه سوال", "پاسخ تشریحی"],
    "price_toman": 30000,
    "media_type": "pdf",
    "telegram_file_id": "BQAC..."
  }]}'
```

- درخت دانشگاه ← درس ← استاد خودکار find-or-create و تأیید می‌شه (دانشکده پیش‌فرض: «سایر»)
- استاد خالی ← «نامشخص» · عنوان خالی ← خودکار از نوع+درس+استاد+ترم ساخته می‌شه
- **پست‌های متنی** (`media_type: "text"` + `body`) به فایل `.txt` تبدیل و آپلود می‌شن
- هر آیتم جداگانه جواب می‌گیره — خطای یکی، بقیه رو نمی‌خرابه: `{imported, failed, results[]}`
- ⚠️ `telegram_file_id` باید متعلق به بات نوت‌بازار باشه — file_id بات کراولر برای دانلود معتبر نیست؛
  راه‌حل: فایل رو مستقیم با `POST /import/notes` (multipart) آپلود کن یا به بات فوروارد کن

### تک‌فایل (multipart)

```bash
curl -X POST http://localhost:8311/import/notes \
  -H "X-Bot-Secret: $API_SECRET" -H "X-Telegram-Id: $ADMIN_TG_ID" \
  -F "university=دانشگاه صنعتی شریف" -F "course=ریاضی ۱" -F "professor=دکتر احمدی" \
  -F "title=ریاضی ۱ — نمونه سوال" -F "kind=نمونه سوال پایانترم" -F "term=4041" \
  -F "tags=نمونه سوال, جمع‌بندی" -F "price_toman=30000" -F "file=@notes.pdf"
```

## تست فلو

۱. `/start` توی بات ← ثبت‌نام خودکار
۲. «💰 کیف پول» ← «شارژ تستی» (ادمین)
۳. «➕ فروش جزوه» ← فایل ← عنوان ← توضیح ← قیمت ← ترم ← تگ‌ها ← **نوع مدرک** ← درخت
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
- [ ] خرید مستقیم از سایت با اکانت ایمیلی (الان فقط مشاهده حسابه)
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
