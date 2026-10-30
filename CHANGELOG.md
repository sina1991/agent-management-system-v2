# Changelog

## 0.6.0 — 2026-10-30

اولین نسخهٔ شماره‌گذاری‌شدهٔ پروژه، در وضعیت **Public Preview**.

### موارد افزوده‌شده

- Contracts، Task State Machine و Storage مبتنی بر SQLite با migrations صریح.
- Agent Registry و Worker داخلی با اجرای محدود، timeout و retry.
- ثبت مستقل Execution و Result و بازیابی پس از crash.
- نصب محلی یا از HTTPS source، اعتبارسنجی نصب و وابستگی‌های قفل‌شده.
- APIهای ذخیره‌سازی Approval، Handoff و Context نسخه‌دار.
- Backup و Restore پایگاه داده.

### محدودیت‌های شناخته‌شده

- Heartbeat پیوسته و هماهنگی چند Orchestrator/Worker هنوز پیاده‌سازی نشده‌اند.
- CLI کامل Handoff، امضای bundle و اتصال Approval به همهٔ عملیات حساس باقی مانده است.
- Backup فعلی Artifactها را شامل نمی‌شود.
- Recovery خودکار crash هنگام نصب و upgrade و آزمون‌های سرتاسری انتشار باقی مانده‌اند.

برای وضعیت دقیق و معیارهای پذیرش، [Roadmap](docs/roadmap.md) را ببینید.
