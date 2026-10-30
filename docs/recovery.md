# ذخیره Execution، Result و Recovery

Migration `0002` جداول مستقل `executions` و `results` را می‌سازد. Unique constraint روی `idempotency_key` و Result برای هر Execution تکرار ثبت را متوقف می‌کند. شروع Execution، پایان Execution/Result و Eventهایشان پایدارند. شمار Attempts از جداول Execution خوانده می‌شود.

برای Database قدیمی، ابتدا Backup خارج از مخزن ایجاد کنید، سپس `ams db upgrade DATABASE` را اجرا کنید. این فرمان پیش از Upgrade از SQLite Backup API استفاده می‌کند و نسخه قبلی را در فایل `.pre-upgrade.bak` کنار Database نگه می‌دارد. اگر ارتقا شکست بخورد، فایل Database از Backup بازگردانده می‌شود. وجود Backup هم‌نام مانع اجرای بعدی می‌شود تا ابتدا آن را بررسی کنید. `ams db verify` نسخه Schema را بررسی می‌کند و خودش Upgrade انجام نمی‌دهد.

`ams recover DATABASE` اجراهای دارای Lease منقضی را اتمی به Execution=`unknown` و Result=`unknown` تبدیل می‌کند و Task درحال اجرا را به FAILED می‌برد. اجرای دوباره Recovery همان Attempt را تکرار نمی‌کند. Result مبهم retryable نیست؛ اجرای مجدد باید پس از بررسی انسانی و سیاست اثر عملیات انجام شود.

Recovery مبتنی بر Lease است، نه اثبات پایان Process خارجی. Worker فعلی بدون اثر جانبی طراحی شده است؛ برای Runtime دارای اثر بیرونی، اجرای Task نامشخص نباید خودکار تکرار شود. Lease دقیق، Heartbeat پیوسته و مالکیت چند Orchestrator در این مرحله وجود ندارند.
