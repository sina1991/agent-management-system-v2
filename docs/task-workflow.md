# مسیر Task نسخه MVP

با `ams agent register DATABASE examples/agent-text-echo.json` یک Worker داخلی مشخص ثبت کنید. Workerهای فعلی `text.echo` و `math.sum` هستند و فقط فیلدهای ورودی اعلام‌شده را می‌پذیرند. کد دلخواه از Database یا Task بارگذاری و اجرا نمی‌شود.

Task باید `verification_spec.verifier` برابر `json_equals` داشته باشد و `parameters.expected` نتیجه دقیق را مشخص کند. پس از ساخت Task، `ams task run DATABASE TASK_UUID` یک Agent دارای قابلیت `task.execute` را انتخاب می‌کند، Task را از CREATED تا RUNNING می‌برد، Execution و Result را در Configuration Database ذخیره می‌کند، سپس با مقایسه JSON نتیجه آن را Verify می‌کند. تنها نتیجه منطبق به COMPLETED می‌رسد. شکست Worker به FAILED و شکست Verify به CHANGES_REQUESTED می‌رود.

این مسیر synchronous و یک‌باراجراست. timeout فعلاً در Contract ثبت می‌شود اما اجرای in-process را قطع نمی‌کند؛ lease، retry خودکار، Artifact filesystem، Worker process isolation و concurrency هنوز آماده نیستند. Workerها کد مورد اعتماد خود مخزن‌اند، Sandbox محسوب نمی‌شوند. Execution و Result در حال حاضر JSON داخل جدول configuration هستند؛ Migration مستقل و queryهای تخصصی آن‌ها مرحله بعد است.
