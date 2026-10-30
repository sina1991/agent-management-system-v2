# Agent Management System V2

سیستم مستقل مدیریت Agent و Task که داخل هر Target Repository نصب خواهد شد.

## وضعیت فعلی

Contracts، Task State Machine و Storage اولیه SQLite پیاده‌سازی شده‌اند. Task، Event و Configuration پس از Restart حفظ می‌شوند. Installer محلی و doctor هم اکنون برای Targetهای Git پیاده‌سازی شده‌اند. Agent Registry عملیاتی و Runtime هنوز پیاده‌سازی نشده‌اند. این مخزن به V1 وابسته نیست.

## اجرای نسخه توسعه

Python 3.12 مبنای فعلی است.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c requirements.lock.txt -e .
ams --version
ams status
python -m unittest discover -s tests -v
```

`ams status` وضعیت توسعه نرم‌افزار را گزارش می‌کند؛ نصب در Target انجام نمی‌دهد.

## دستورات فعلی

```bash
ams schema Task
ams validate Task examples/task.json
ams db init /tmp/ams-demo/system.db
ams task create /tmp/ams-demo/system.db examples/task.json
ams db verify /tmp/ams-demo/system.db
```

برای نصب نسخه فعلی روی یک Checkout آزمایشی Git:

```bash
ams install /path/to/target-repository
ams doctor /path/to/target-repository
```

Installer کد نسخه فعلی Package را در `.agent-system/app/` کپی می‌کند، SQLite را آماده می‌کند و Manifest دارای Checksum می‌نویسد. این نصب Target از Source Repository یا URL دریافت نمی‌کند و محیط مجازی یا Dependencyهای Target را نصب نمی‌کند؛ Python باید Pydantic، SQLAlchemy و Alembic را از قبل داشته باشد. مسیر Target نباید پوشه رزروشده `.agent-system/` با محتوای قبلی داشته باشد.

`task create` شناسه Task را برمی‌گرداند. سپس با `ams task show DATABASE UUID` و `ams task history DATABASE UUID` اطلاعات آن را بخوانید. این دستورات Task را اجرا نمی‌کنند.

`db init` فقط Database خالی را مقداردهی اولیه می‌کند؛ Schema ناشناخته را تغییر نمی‌دهد. Database آزمایشی را خارج از Git نگه دارید. محدودیت‌های فعلی و مرزهای API در [Contracts و Storage](docs/contracts-and-storage.md) آمده‌اند.

## مستندات

- [Specification 1.1](docs/specification.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [ADRs](docs/adr/README.md)
- [مشارکت](CONTRIBUTING.md)

اولین Milestone عملی: Install → Verify → Register Agent → Create Task → Execute → Validate Result → Report.

License توزیع عمومی هنوز توسط مالک انتخاب نشده است.
