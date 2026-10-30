# Contracts و Storage

هشت Contract نسخه 1.0 با Pydantic تعریف شده‌اند: Agent، Task، Message، Execution، Result، Event، Approval و Artifact. نسخه Contract با Specification 1.1 مستقل است. JSON Schema با `ams schema NAME` تولید می‌شود. Unknown Field، Timestamp بدون Timezone و Schema Version ناشناخته رد می‌شوند. Timestampها به UTC تبدیل می‌شوند.

Task از Execution Attempt جداست. Result موفق بدون Verify، Task را COMPLETED نمی‌کند. Artifact Path در سطح Contract بررسی می‌شود؛ بررسی Symlink و دسترسی واقعی به فایل وظیفه Runtime آینده است.

Domain شامل State Machine، Dependency DAG، Permission Decision و Error Code است و به Database وابسته نیست. Application تغییر Task و Event مربوط را تولید می‌کند. TransitionFacts ورودی قابل اعتماد از سرویس هماهنگ‌کننده است؛ نباید مستقیماً از درخواست کاربر یا Agent پذیرفته شود. Runtime و Verifier واقعی هنوز ساخته نشده‌اند، بنابراین Guards جایگزین شواهد واقعی اجرا نیستند.

Store با SQLAlchemy و Alembic از SQLite محلی استفاده می‌کند. Migration اولیه همراه Python Package نصب می‌شود. create_task و transition تغییر Task و Event را در یک Transaction ثبت می‌کنند. شکست نوشتن Event باعث Rollback تغییر Task می‌شود. Revision قدیمی رد می‌شود و Dependencyها از State ذخیره‌شده خوانده می‌شوند.

Schema فعلی شامل tasks، events و configuration است. Agent، Execution، Result و Approval فعلاً Contract هستند؛ Registry و ذخیره آن‌ها در مراحل بعد اضافه می‌شود. Configuration یک API داخلی برای داده اشتراکی است و Secret Vault یا Context Retrieval کامل نیست.

`initialize` فقط Database تمیز را ایجاد می‌کند یا Schema فعلی را Verify می‌کند. Migration خودکار Schema ناشناخته یا Upgrade محصول انجام نمی‌شود. این نسخه فقط یک Writer عملیاتی را هدف می‌گیرد؛ Stress Test چند Writer و PostgreSQL پشتیبانی اعلام‌شده نیستند.

تست‌ها شامل Restart، جداسازی دو Database، Rollback شکست Event، شکست Migration، Revision قدیمی، Dependency نامعتبر، Approval منقضی و رد انتقال نامجاز هستند. محدودیت نسخه‌های تست‌شده در requirements.lock.txt برای Python 3.12 روی Linux ثبت شده است؛ این فایل تضمین نصب Offline یا Lock چندپلتفرمی نیست.
