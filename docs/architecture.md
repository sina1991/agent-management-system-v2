# معماری اجرایی

Domain مستقل از Storage، Provider و Interface است. Application چرخه Task و Policy را هماهنگ می‌کند. Infrastructure مالک SQLite و Migration آینده است. Runtime تنها Workerهای مشخص و مورد اعتماد MVP را اجرا خواهد کرد.

Source محصول قابل توزیع را می‌سازد. Target کد Release را در .agent-system/app و State خصوصی را در .agent-system/state نگه می‌دارد. پس از آماده‌شدن Dependencies، اجرای محلی به Source وابسته نیست.

Installer Alpha و Local Alpha دو Role مکالمه‌اند. CLI عملیات قطعی را انجام می‌دهد. Context و Database ادامه کار در Conversation جدید را ممکن می‌کنند.

ساختار فعلی فقط Foundation است؛ مرزهای ماژول‌ها ایجاد شده‌اند و رفتار عملیاتی در مراحل بعد افزوده می‌شود.
