# Agent Management System V2

سیستم مستقل مدیریت Agent و Task که داخل هر Target Repository نصب خواهد شد.

**نسخه: 0.6.0 — Public Preview**

## وضعیت فعلی

Contracts، Task State Machine و Storage مبتنی بر SQLite پیاده‌سازی شده‌اند. Task، Execution، Result و Event پس از Restart حفظ می‌شوند. Installer، doctor، Agent Registry و Workerهای داخلی در دسترس‌اند. مسیر synchronous اجرای Task تا Verify، retry محدود و Recovery پایه پیاده‌سازی شده است. این مخزن به V1 وابسته نیست.

## نصب و اجرای نسخه 0.6.0

Python 3.12 مبنای فعلی است.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c requirements.lock.txt -e .
ams --version
ams status
python -m unittest discover -s tests -v
```

`ams status` وضعیت توسعهٔ نرم‌افزار را گزارش می‌کند؛ نصب در Target انجام نمی‌دهد.

## دستورات فعلی

```bash
ams schema Task
ams validate Task examples/task.json
ams db init /tmp/ams-demo/system.db
ams agent register /tmp/ams-demo/system.db examples/agent-text-echo.json
ams task create /tmp/ams-demo/system.db examples/task.json
ams db verify /tmp/ams-demo/system.db
```

برای نصب روی یک Checkout آزمایشی Git:

```bash
ams install /path/to/target-repository --source-url https://github.com/OWNER/agent-management-system-v2.git
ams doctor /path/to/target-repository
```

Installer از HTTPS source بدون اطلاعات ورود در URL پشتیبانی می‌کند، وابستگی‌های قفل‌شده را در محیط Target نصب می‌کند و Manifest دارای Checksum می‌نویسد. مسیر Target نباید پوشهٔ رزروشدهٔ `.agent-system/` با محتوای قبلی داشته باشد.

`task create` شناسه Task را برمی‌گرداند؛ سپس `ams task run DATABASE UUID` مسیر اجرا و Verify را طی می‌کند؛ برای خطای Timeout می‌توان با `ams task retry DATABASE UUID` یک Attempt جدید درخواست کرد. مثال فعلی برای تکمیل موفق Task باید `verification_spec` را روی `json_equals` با خروجی مورد انتظار قرار دهد. `manual_review` به‌طور خودکار COMPLETED نمی‌شود. سپس با `ams task show DATABASE UUID` و `ams task history DATABASE UUID` اطلاعات آن را بخوانید.

`db init` فقط Database خالی را مقداردهی اولیه می‌کند؛ Schema ناشناخته را تغییر نمی‌دهد. Database آزمایشی را خارج از Git نگه دارید. محدودیت‌های فعلی و مرزهای API در [Contracts و Storage](docs/contracts-and-storage.md) آمده‌اند.

## Backup و Context

```bash
ams backup /path/to/system.db /path/to/snapshot.db
ams restore /path/to/snapshot.db /path/to/new-system.db
ams context set /path/to/system.db project.summary '{"name":"Demo"}'
ams context get /path/to/system.db project.summary
ams db upgrade /path/to/system.db
ams db verify /path/to/system.db
```

## مستندات

- [Specification 1.1](docs/specification.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Backup و Restore](docs/backup-restore.md)
- [Approval، Handoff و Context](docs/collaboration-context.md)
- [تاریخچه نسخه‌ها](CHANGELOG.md)
- [ADRs](docs/adr/README.md)
- [مشارکت](CONTRIBUTING.md)

اولین Milestone عملی: Install → Verify → Register Agent → Create Task → Execute → Validate Result → Report.

License توزیع عمومی هنوز توسط مالک انتخاب نشده است.
