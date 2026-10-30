# Backup و Restore

`ams backup DATABASE DESTINATION` با SQLite Backup API Snapshot سازگار می‌سازد. مقصد باید جدید باشد و نسخه Schema و Integrity پیش از نهایی‌شدن بررسی می‌شوند. `ams restore BACKUP NEW_DATABASE` نیز فقط در مسیر جدید Restore می‌کند و Database موجود را Overwrite نمی‌کند.

این فرمان‌ها Database را پوشش می‌دهند. Artifacts و تنظیمات بیرون Database هنوز Backup Bundle مشترک ندارند. برای Upgrade از `0001` یا `0002` به نسخه جدید، `ams db upgrade DATABASE` نسخه پیشین را با نام timestamp دار کنار Database نگه می‌دارد. `ams db verify` پس از Upgrade را اجرا کنید.
