# Agent Management System V2

سیستم مستقل مدیریت Agent و Task که داخل هر Target Repository نصب خواهد شد.

## وضعیت فعلی

مرحله Foundation: ساختار Python، CLI پایه و مستندات طراحی آماده‌اند. Installer، Database، Registry و Runtime هنوز پیاده‌سازی نشده‌اند. این مخزن به V1 وابسته نیست.

## اجرای نسخه توسعه

Python 3.12 مبنای فعلی است.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
ams --version
ams status
python -m unittest discover -s tests -v
```

`ams status` فقط وضعیت Foundation را گزارش می‌کند؛ نصب در Target انجام نمی‌دهد. دستورات آینده در Specification آمده‌اند و هنوز قابل اجرا نیستند.

## مستندات

- [Specification 1.1](docs/specification.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [ADRs](docs/adr/README.md)
- [مشارکت](CONTRIBUTING.md)

اولین Milestone عملی: Install → Verify → Register Agent → Create Task → Execute → Validate Result → Report.

License توزیع عمومی هنوز توسط مالک انتخاب نشده است.
