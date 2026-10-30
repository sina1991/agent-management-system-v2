# Installer و doctor فعلی

`ams install TARGET` نسخه Package فعلی را از Python Environment در Target دارای Git کپی می‌کند. Release در `.agent-system/app/<version>/agent_system/` ذخیره می‌شود. State در `.agent-system/state/system.db` و تنظیمات اولیه در `.agent-system/config/system.json` قرار می‌گیرند. `profiles/` فعلاً خالی است.

Installer به Target موجود و Git Checkout نیاز دارد. با `--source-url` از HTTPS Git clone محدود دریافت می‌کند، Revision و Version را ثبت می‌کند و در Target دارای Network، `.venv` می‌سازد و Dependencyهای قفل‌شده را نصب می‌کند. بدون این گزینه از نسخه Package جاری استفاده می‌کند. Installer هیچ Clone یا Push برای Target انجام نمی‌دهد و Working Tree Target را تغییر نمی‌دهد. Python اجرایی باید Pydantic، SQLAlchemy و Alembic داشته باشد. این انتخاب فعلی محدودیت Foundation است؛ Installer کامل مطابق Specification باید Source URL، دسترسی و آماده‌سازی Dependencies را پوشش دهد.

نصب تکراری فقط پس از Verify Manifest، Checksum فایل‌ها و Database به‌عنوان `existing` گزارش می‌شود. نصب نامعتبر یا Manifest ناسازگار متوقف می‌شود. محتوای قبلی زیر `.agent-system/` بدون Manifest تغییر نمی‌کند. فایل‌های عملیاتی Target در `.gitignore` الگو دارند.

`ams doctor TARGET` نسخه، Inventory فایل و Database را Verify می‌کند. Repair یا Upgrade انجام نمی‌دهد. تغییر Release باید از مسیر نسخه جدید و Upgrade با Backup انجام شود؛ Upgrade هنوز پیاده‌سازی نشده است.

آزمون‌ها Target موقت با `.git` ساختگی ایجاد می‌کنند و نگهداشت داده، نصب مجدد، مسیر نامعتبر، محتوای رزروشده و تشخیص دستکاری Release را بررسی می‌کنند. این تست‌ها Git Clone واقعی یا دسترسی Remote را شبیه‌سازی نمی‌کنند.
