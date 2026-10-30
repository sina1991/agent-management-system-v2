# Timeout و Retry

Worker داخلی در Process جداگانه با `python -I` اجرا می‌شود. ورودی و خروجی JSON محدودند، Environment فرزند به متغیرهای پایه محدود می‌شود و استثنای داخلی Worker به کاربر نشت نمی‌کند. Timeout واقعی Process را می‌بندد و نتیجه `WORKER_TIMEOUT` ثبت می‌شود. این جداسازی Sandbox امنیتی نیست؛ Workerهای allowlist باید مورد اعتماد و بدون اثر جانبی باشند.

Retry خودکار نیست. پس از Timeout، کاربر یا Orchestrator می‌تواند `ams task retry DATABASE TASK_UUID` اجرا کند. سقف Attempts سه است و هر بار `execution_id` و `idempotency_key` جدید می‌گیرد. Retry فقط برای Resultای مجاز است که `retryable=true` داشته باشد. شکست Verify، خطای ورودی و خطای عمومی Worker به‌طور خودکار قابل Retry نیستند.

خروجی مبهم در این Workerهای بدون اثر جانبی پس از Timeout قابل تکرار است. برای Runtimeهای دارای اثر جانبی، Timeout به معنی نامشخص‌بودن اثر عملیات است و retry خودکار باید تا پیاده‌سازی Idempotency و Recovery مسدود بماند.

محدودیت‌های باز: Lease Recovery پس از Crash کامل Orchestrator، مالکیت چند Worker، Heartbeat واقعی، Cancel API و persistence اختصاصی Execution جدول مستقل هنوز وجود ندارند. وضعیت Attemptها موقتاً در جدول configuration ذخیره می‌شود.
