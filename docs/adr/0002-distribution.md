# ADR 0002 — Distribution

Release مستقل در Target قرار می‌گیرد. app، config و state جدا هستند. Manifest نسخه، شناسه نصب و Checksums را ثبت می‌کند. نصب Staging و Lock دارد و نصب مجدد داده را حذف نمی‌کند. Upgrade اختیاری با Backup و Migration آزموده‌شده است. نصب Offline کامل خارج از MVP است.
