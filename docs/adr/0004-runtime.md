# ADR 0004 — Runtime boundary

MVP فقط Workerهای مورد اعتماد و مشخص را اجرا می‌کند. subprocess و Timeout ادعای Sandbox ایجاد نمی‌کنند. Permission غیرقابل اعمال رد می‌شود. اجرای کد نامطمئن و چند Agent تغییردهنده هم‌زمان خارج از MVP هستند.
