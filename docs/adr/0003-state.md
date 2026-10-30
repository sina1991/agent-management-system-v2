# ADR 0003 — State and execution

SQLite منبع حقیقت هر Target است. Task از Execution Attempt جداست. Queue دارای at-least-once semantics است. Lease، Owner Token و Idempotency لازم‌اند. اثر نامشخص مجوز Retry خودکار ندارد. State و Event در Transaction مشترک ثبت می‌شوند. MVP یک Writer عملیاتی دارد.
