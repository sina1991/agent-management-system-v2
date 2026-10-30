# Approval، Handoff و Project Context

Migration `0003` جدول‌های `approvals`، `handoffs` و `project_context` را می‌سازد. Approval تصمیم یک‌باره دارد و به `action_digest`، Scope و Policy Version متصل است. Handoffهای ثبت‌شده به Task و Execution همان Target وصل‌اند و `payload_digest` هنگام ساخت Contract بررسی می‌شود. Payload شامل JSON داده است و هرگز به‌عنوان Command اجرا نمی‌شود.

`ams context set DATABASE KEY JSON_VALUE` و `ams context get DATABASE KEY` برای Project Context محلی هستند. هر نوشتن Revision را زیاد می‌کند و `expected_revision` در API برای رد Lost Update استفاده می‌شود. Namespace هر Target مستقل است. تفکیک Context خصوصی و اشتراکی و بازیابی Conversation توسط AI هنوز نیاز به تکمیل دارد.

API پایه Approval و Handoff آماده است؛ CLI کامل Export/Import و ورود نتیجه Handoff به Execution در مرحله بعد تکمیل می‌شوند. Approval فعلی تصمیم را ذخیره می‌کند؛ اتصال آن به همه عملیات حساس Runtime هنوز کامل نیست.
