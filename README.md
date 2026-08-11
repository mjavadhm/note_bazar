# NoteBazar 🎓 — جزوه‌بازار

بات تلگرام + سایت + مینی‌اپ برای خرید و فروش جزوه دانشجویی — با کیف پول داخلی،
پیش‌نمایش واترمارک‌دار، امتیاز و نظر، خواننده آنلاین با واترمارک شخصی،
ایمپورت انبوه از کانال‌های کراول‌شده، و جستجو بر اساس دانشگاه ← دانشکده ← درس ← استاد
+ سال/ترم و تگ.

## معماری

```
Telegram User ──▶ bot (aiogram) ──┐
Browser ────────▶ web (nginx) ────┤
Telegram MiniApp (viewer) ────────┤
Crawler ────────▶ /import/notes ──┤
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

| سرویس | نقش |
|---|---|
| `api` | FastAPI — کاربر، درخت، جزوه (با ترم و تگ)، خرید، کیف پول، ادمین + عمومی + مینی‌اپ + ایمپورت |
| `bot` | aiogram 3 — فقط UI؛ هیچ دسترسی مستقیم به دیتابیس نداره |
| `web` | nginx — سایت (index/note) + مینی‌اپ (library/viewer) + پروکسی `/api` به بک‌اند |
| `worker` | Celery — ساخت پیش‌نمایش واترمارک‌دار از PDFها |
| `db` / `redis` / `minio` | Postgres 16، Redis، MinIO به‌عنوان S3 |

## راه‌اندازی (۳ قدم)

```bash
cp .env.example .env   # توکن BotFather + آیدی عددی خودت (ADMIN_TELEGRAM_IDS)
docker compose up --build -d
```

| آدرس | چیه |
|---|---|
| http://localhost:8080 | 🌐 سایت |
| http://localhost:8000/docs | مستندات API (Swagger) |
| http://localhost:9001 | کنسول MinIO (minio / minio123) |

- یوزرنیم باتت رو توی `web/config.js` بذار تا دکمه‌های «خرید در تلگرام» کار کنن.
- برای دکمه «📖 مطالعه آنلاین» داخل بات، `MINIAPP_URL` رو توی `.env` بذار (HTTPS لازمه).
- پیش‌نمایش سایت بدون بک‌اند: `index.html?demo=1`

## 🕷️ ایمپورت از کراولر

اندپوینت `POST /import/notes` (فقط ادمین) برای تزریق جزوه‌های کراول‌شده از کانال‌ها.
درخت دانشگاه/درس/استاد خودکار **find-or-create** و مستقیم **تأیید** می‌شه (دانشکده پیش‌فرض: «سایر»).
فایل رو می‌تونی مستقیم آپلود کنی یا `telegram_file_id` بدی:

```bash
curl -X POST http://localhost:8000/import/notes \
  -H "X-Bot-Secret: $API_SECRET" -H "X-Telegram-Id: $ADMIN_TG_ID" \
  -F "university=دانشگاه صنعتی شریف" \
  -F "course=ریاضی ۱" \
  -F "professor=دکتر احمدی" \
  -F "title=ریاضی ۱ — نمونه سوال ۱۰ ترم اخیر" \
  -F "term=بهار ۱۴۰۴" \
  -F "tags=نمونه سوال, جمع‌بندی" \
  -F "price_toman=30000" \
  -F "file=@notes.pdf"
```

- `tags` با کاما (یا «،») جدا می‌شه — حداکثر ۱۰ تا
- `term` آزاد: «بهار ۱۴۰۴»، «۱۴۰۳»، هرچی کراولر استخراج کرده
- بعد از ایمپورت، تسک ساخت پیش‌نمایش خودکار صف می‌شه
- فیلتر و جستجو: `GET /public/notes?tag=نمونه سوال&term=بهار ۱۴۰۴` و جستجوی متنی روی تگ‌ها هم کار می‌کنه

## تست فلو

۱. توی بات `/start` بزن.
۲. چون ادمینی: «💰 کیف پول» ← «شارژ تستی».
۳. «➕ فروش جزوه» ← فایل، عنوان، توضیح، قیمت، **ترم**، **تگ‌ها** ← انتخاب درخت (یا «پیشنهاد جدید»).
۴. `/panel` ← تأیید جزوه و پیشنهادهای درخت.
۵. «🔍 جستجو» ← «👁 پیش‌نمایش» ← «🛒 خرید» ← فایل کامل + امتیاز.

## تصمیم‌های طراحی

- **احراز بات→API:** سکرت مشترک + هدر `X-Telegram-Id`. مینی‌اپ: اعتبارسنجی `initData` تلگرام.
- **کیف پول:** Ledger غیرقابل‌تغییر؛ موجودی محاسبه‌ای. درگاه واقعی فعلاً نیومده (شارژ تستی ادمین).
- **خرید:** آزادسازی فوری + کمیسیون. قلاب escrow: `Purchase.status`.
- **ضد کپی:** پیش‌نمایش عمومی واترمارک‌دار + خواننده آنلاین مینی‌اپ با **واترمارک شخصی خریدار**.
- **فایل‌ها:** هر فرمتی برای آپلود؛ پیش‌نمایش/خواندن آنلاین فعلاً فقط PDF.
- **اسکیما:** `create_all` — اگه قبلاً بالا آوردی، بعد از این تغییرات یه بار `docker compose down -v` کن.

## گام‌های بعدی

- [ ] Alembic برای migration به‌جای `create_all`
- [ ] درگاه پرداخت (زرین‌پال) + تسویه فروشنده
- [ ] `delivery_mode` روی جزوه (فقط آنلاین / دانلود واترمارک‌دار / دانلود آزاد) — انتخاب فروشنده
- [ ] escrow: `held` + آزادسازی خودکار بعد از ۲۴ ساعت (Celery beat)
- [ ] گزارش تخلف + refund
- [ ] صفحه‌بندی نتایج + فیلتر تگ/ترم توی UI سایت

## ساختار پوشه‌ها

```
notebazar/
├── docker-compose.yml
├── .env.example
├── api/              # FastAPI + SQLAlchemy + boto3 + PyMuPDF
│   └── app/
│       ├── routers/           # taxonomy, notes, purchases, wallet, admin, public, miniapp, importer
│       ├── miniapp_security.py# اعتبارسنجی initData + توکن داخلی
│       ├── personal_render.py # رندر صفحه با واترمارک شخصی
│       └── ...
├── bot/              # aiogram 3 — فلوی فروش با ترم و تگ
├── worker/           # Celery — پیش‌نمایش واترمارک‌دار PDF
└── web/              # سایت + مینی‌اپ (vanilla JS)
    ├── index.html / note.html / library.html / viewer.html
    ├── config.js              # ⚙️ یوزرنیم بات
    ├── nginx.conf             # پروکسی /api
    └── assets/                # styles.css, app.js, site.js, miniapp.js
```
