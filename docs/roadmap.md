# مراحل اجرا

| مرحله | خروجی | معیار پذیرش | وضعیت |
| --- | --- | --- | --- |
| 0 | Specification و ADR | تصمیم‌ها ثبت شوند | ثبت شده |
| 1 | Python Package، CLI و CI | نصب تمیز و CI موفق | CI اولیه موفق؛ توسعه یافته |
| 2 | Contracts و State Machine | ورودی و انتقال نامعتبر رد شوند | پیاده‌سازی و تست شده |
| 3 | Storage و Events | حفظ داده پس از Restart | Storage اولیه Task/Event/Config پیاده‌سازی و تست شده |
| 4 | Installer و doctor | نصب مجدد بدون حذف داده | نصب محلی و doctor پایه پیاده‌سازی شده؛ Source URL، Dependencies و Recovery نصب ناتمام باقی است |
| 5 | مسیر کامل یک Task | اجرای Task تا Verify واقعی | پیاده‌سازی MVP synchronous انجام شد؛ retry و recovery در مرحله 6 باقی است |
| 6 | Recovery اجرا | مدیریت قطع Worker و نتیجه دیررس | برنامه‌ریزی شده |
| 7 | Handoff و Policy | Import معتبر و Approval دقیق | برنامه‌ریزی شده |
| 8 | Context و Alpha | ادامه Conversation و جداسازی Target | برنامه‌ریزی شده |
| 9 | Backup، Upgrade و Release | Restore و استقلال Source آزموده شوند | برنامه‌ریزی شده |

Gateهای دقیق در فصل 24 Specification آمده‌اند. موفقیت CI باید برای Commit مربوط مشاهده شود و از وجود فایل Workflow استنتاج نشود.
