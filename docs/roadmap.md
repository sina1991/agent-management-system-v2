# مراحل اجرا

| مرحله | خروجی | معیار پذیرش | وضعیت |
| --- | --- | --- | --- |
| 0 | Specification و ADR | تصمیم‌ها ثبت شوند | ثبت شده |
| 1 | Python Package، CLI و CI | نصب تمیز و CI موفق | CI اولیه موفق؛ توسعه یافته |
| 2 | Contracts و State Machine | ورودی و انتقال نامعتبر رد شوند | پیاده‌سازی و تست شده |
| 3 | Storage و Events | حفظ داده پس از Restart | Storage اولیه Task/Event/Config پیاده‌سازی و تست شده |
| 4 | Installer و doctor | نصب مجدد بدون حذف داده | نصب محلی و doctor پایه پیاده‌سازی شده؛ Source URL، Dependencies و Recovery نصب ناتمام باقی است |
| 5 | مسیر کامل یک Task | اجرای Task تا Verify واقعی | پیاده‌سازی MVP synchronous انجام شد؛ retry و recovery در مرحله 6 باقی است |
| 6 | Recovery اجرا | اجرای محدود، Timeout و Retry صریح | Worker Process، Timeout واقعی و سقف سه Attempt برای Timeout پیاده‌سازی شد؛ Execution/Result مستقل، Upgrade صریح و Recovery idempotent پیاده‌سازی شد؛ Heartbeat پیوسته، چند Orchestrator و چند Worker باقی است |
| 7 | Handoff و Policy | Import معتبر و Approval دقیق | جدول‌ها و API ذخیره و تصمیم Approval/Handoff آماده؛ CLI کامل، امضای Bundle و اتصال Policy به Runtime باقی است |
| 8 | Context و Alpha | Context هر Target و ادامه Conversation | جدول Context و Revision پیاده‌سازی شد؛ تفکیک private/shared و Alpha handoff باقی است |
| 9 | Backup، Upgrade و Release | Backup، Restore و Release | Backup/Restore پایگاه داده و Migrationهای صریح پیاده‌سازی شدند؛ Artifact Bundle و آزمون Upgrade/Release سرتاسری باقی است |

Gateهای دقیق در فصل 24 Specification آمده‌اند. موفقیت CI باید برای Commit مربوط مشاهده شود و از وجود فایل Workflow استنتاج نشود.
