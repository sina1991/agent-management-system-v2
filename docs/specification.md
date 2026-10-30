# Agent Management System V2

## System Specification & Architecture --- Final Design

**Document Status:** Final Design Baseline\
**Version:** 1.1\
**Project:** Agent Management System V2\
**Source Repository:**
https://github.com/sina1991/agent-management-system-v2\
**Architecture:** Repository-Embedded, Self-Contained, Hybrid &
Extensible

------------------------------------------------------------------------

# 1. چشم‌انداز محصول (Product Vision)

Agent Management System V2 یک سیستم مستقل و توسعه‌پذیر برای مدیریت،
هماهنگ‌سازی و نظارت بر فعالیت Agentهای هوش مصنوعی و انسانی است.

هدف سیستم، ایجاد یک محیط مدیریتی مستقل درون هر Target Repository است تا
چرخه کامل مدیریت پروژه را از دریافت درخواست تا برنامه‌ریزی، اجرا، ارزیابی
و تحویل نتیجه مدیریت کند.

V2 باید بتواند:

1.  Agentها را ثبت، شناسایی و مدیریت کند.
2.  قابلیت‌ها و محدودیت‌های هر Agent را بشناسد.
3.  درخواست‌های کاربر را به Taskهای قابل اجرا تقسیم کند.
4.  Taskها را به Agent مناسب تخصیص دهد.
5.  اجرای Taskها را مدیریت و نظارت کند.
6.  خروجی Agentها را دریافت و اعتبارسنجی کند.
7.  ارتباط و تبادل اطلاعات بین Agentها را مدیریت کند.
8.  Context و تاریخچه پروژه را نگهداری کند.
9.  در موارد ضروری تأیید انسانی دریافت کند.
10. Runtime، Provider و Integrationهای جدید را بدون بازطراحی هسته
    بپذیرد.

V2 یک محصول مستقل است و نباید به معماری، کد یا سرویس‌های V1 وابسته باشد.
V1 باید بدون تغییر به فعالیت خود ادامه دهد.

# 2. اصل بنیادی معماری

## Repository-Embedded, Self-Contained Agent Management System

هر Target Repository باید محیط مدیریتی مستقل خودش را داشته باشد.

پس از نصب V2 در Target:

-   نسخه مستقل V2 داخل همان Repository قرار می‌گیرد.
-   Local Alpha همان Target مدیریت پروژه را بر عهده می‌گیرد.
-   Agent Registry، Task Manager و Database مستقل خواهند بود.
-   Context، History، Logs و Artifacts مستقل خواهند بود.
-   تنظیمات و Policyها مستقل خواهند بود.
-   اطلاعات و عملیات Targetهای مختلف با یکدیگر مخلوط نمی‌شوند.

Source Repository فقط منبع توزیع اولیه و دریافت Upgradeهای اختیاری V2
است. پس از نصب، عملکرد روزمره Target نباید به Source Repository وابسته
باشد.

**Target Repository مالک محیط عملیاتی V2 خود است.**

# 3. معماری Alpha و چرخه تغییر نقش

سیستم از دو Role برای Alpha استفاده می‌کند. این دو Role دو Agent مستقل
نیستند؛ بلکه دو مرحله از چرخه فعالیت یک Agent در همان Conversation
هستند.

## 3.1 Installer Alpha

Installer Alpha نقش اولیه ایجنت در ابتدای Conversation است. مسئولیت آن
آماده‌سازی و نصب V2 در Target Repository است.

وظایف:

1.  دریافت Source Repository URL.
2.  دسترسی به Source Repository و دریافت نسخه کامل V2.
3.  شناسایی اجزای مورد نیاز برای نصب.
4.  دریافت Target Repository URL.
5.  بررسی دسترسی به Target.
6.  تشخیص وجود یا عدم وجود V2 در Target.
7.  بارگذاری نسخه موجود، در صورت نصب قبلی.
8.  نصب خودکار V2، در صورت نبودن آن.
9.  آماده‌سازی تنظیمات اولیه و Database.
10. اجرای تست‌های ضروری نصب.
11. ثبت نسخه و وضعیت نصب.
12. ارائه گزارش نهایی.
13. تغییر Role به Local Alpha.

Installer Alpha مسئول مدیریت پروژه Target نیست. وظیفه آن پس از تحویل
موفق به Local Alpha پایان می‌یابد.

## 3.2 Local Alpha

Local Alpha نقش اصلی و دائمی مدیریت پروژه است و پس از نصب یا شناسایی
موفق V2 در Target فعال می‌شود.

وظایف:

-   مدیریت کامل پروژه و دریافت درخواست‌های کاربر.
-   مدیریت Context و برنامه‌ریزی.
-   مدیریت Agentها و Taskها.
-   تخصیص و نظارت بر اجرای Taskها.
-   بررسی خروجی‌ها و مدیریت خطاها.
-   اجرای چرخه Audit، Apply و Verify.
-   مدیریت مستندات، تاریخچه و Artifacts.
-   نظارت بر عملیات و گزارش وضعیت پروژه.

Local Alpha از اطلاعات و Database موجود در Target استفاده می‌کند.

## 3.3 Role Transition

تغییر نقش باید در همان Conversation اتفاق بیفتد:

`Installer Alpha → Installation/Detection → Verification → Role Transition → Local Alpha`

در این فرآیند:

-   Conversation و Context مکالمه حفظ می‌شوند.
-   ایجنت جدیدی ساخته نمی‌شود.
-   مسئولیت Installer Alpha پایان می‌یابد.
-   Local Alpha مدیریت پروژه را آغاز می‌کند.

اطلاعات واقعی نصب باید از Target Repository و Database خوانده شوند، نه
اینکه صرفاً به حافظه Conversation وابسته باشند.

# 4. چرخه نصب V2

چرخه نصب باید ساده، خودکار و بدون تأییدهای غیرضروری باشد.

## مرحله 1 --- دریافت Source Repository

کاربر آدرس مخزن اصلی V2 را ارسال می‌کند. Installer Alpha به Repository
دسترسی پیدا می‌کند، نسخه V2 را شناسایی می‌کند و بسته کامل نصب را دریافت
می‌کند.

Source V2 باید یک محصول کامل و قابل نصب باشد. Installer Alpha نباید خودش
معماری یا کد V2 را بازسازی کند.

## مرحله 2 --- دریافت Target Repository

کاربر آدرس مخزن پروژه موردنظر را ارسال می‌کند. Installer Alpha آن را
به‌عنوان Target تعیین می‌کند.

## مرحله 3 --- تشخیص وضعیت نصب

Installer Alpha فقط وضعیت نصب V2 را بررسی می‌کند:

-   وجود مسیر اختصاصی V2.
-   وجود Installation Manifest.
-   نسخه نصب‌شده.
-   وضعیت اولیه Database.
-   سازگاری ساختار نصب.

در این مرحله Audit جامع پروژه Target انجام نمی‌شود.

## مرحله 4 --- نصب یا Load

اگر V2 نصب نشده باشد:

-   نسخه کامل V2 داخل Target نصب می‌شود.
-   فایل‌های مورد نیاز ایجاد می‌شوند.
-   Dependencies آماده می‌شوند.
-   تنظیمات اولیه ایجاد می‌شوند.
-   Database مقداردهی اولیه می‌شود.
-   مسیرهای Context، History، Logs و Artifacts آماده می‌شوند.

این عملیات به‌صورت خودکار انجام می‌شود و نیازمند تأیید روتین کاربر نیست.

اگر V2 قبلاً نصب شده باشد:

-   نسخه موجود شناسایی می‌شود.
-   وضعیت نصب بررسی می‌شود.
-   همان نسخه Load می‌شود.
-   داده‌های موجود حفظ می‌شوند.

نصب مجدد نباید باعث حذف Database، History، Artifacts یا اطلاعات موجود
شود.

## مرحله 5 --- Verify

پس از نصب یا Load، موارد ضروری بررسی می‌شوند:

-   صحت ساختار نصب.
-   سازگاری نسخه.
-   دسترسی به Database.
-   صحت تنظیمات اولیه.
-   قابلیت بارگذاری Local Alpha.
-   موفقیت تست‌های ضروری نصب.

موفقیت نصب نباید بدون Verify اعلام شود.

## مرحله 6 --- Report & Handoff

Installer Alpha گزارش نهایی ارائه می‌دهد و مسئولیت مدیریت پروژه را به
Local Alpha منتقل می‌کند.

نمونه وضعیت نصب جدید:

-   Installation: Successful
-   Version: Detected Version
-   Database: Initialized
-   Verification: Passed
-   Role: Local Alpha

نمونه وضعیت نصب قبلی:

-   Installation: Existing
-   Version: Detected Version
-   Database: Existing
-   Verification: Passed
-   Role: Local Alpha

### فرمول نهایی نصب

`Source V2 → Target Repository → Detect Local V2 → Install if Missing → Verify → Report → Local Alpha Handoff`

## مدیریت خطا

اگر Target قابل دسترسی نباشد، مجوز نوشتن وجود نداشته باشد یا نصب شکست
بخورد:

-   خطای واقعی گزارش می‌شود.
-   موفقیت جعلی اعلام نمی‌شود.
-   اطلاعات قبلی حذف نمی‌شوند.
-   سیستم وضعیت ناقص یا ناموفق را ثبت می‌کند.
-   در صورت نیاز، فقط اقدام یا دسترسی ضروری از کاربر درخواست می‌شود.

# 5. معماری کلان سیستم

V2 از پنج لایه اصلی تشکیل می‌شود.

## Layer 1 --- Interface Layer

مسئول ارتباط با کاربر و دریافت درخواست‌ها:

-   CLI
-   API
-   Human Approval Interface
-   Conversation Handoff

## Layer 2 --- Management & Orchestration Layer

مرکز مدیریت سیستم:

-   Local Alpha
-   Agent Registry
-   Task Manager
-   Planner
-   Dispatcher
-   Scheduler
-   Policy Engine

## Layer 3 --- Execution Layer

محیط اجرای وظایف:

-   Internal Runtime
-   External Runtime
-   Workers
-   Execution Manager
-   Result Processor

## Layer 4 --- Integration Layer

ارتباط با سرویس‌ها و محیط‌های بیرونی:

-   GitHub Integration
-   AI Provider Adapters
-   SSH Integration
-   External API Adapters
-   Webhook
-   Manual Handoff

## Layer 5 --- Data & Knowledge Layer

مدیریت اطلاعات و دانش سیستم:

-   Database
-   Project Context
-   Agent Knowledge
-   Task History
-   Execution History
-   Artifacts
-   Logs
-   Event History

# 6. مدیریت Agentها

## Agent Registry

هر Agent باید مشخصات استاندارد داشته باشد:

-   Agent ID
-   Name
-   Role
-   Description
-   Capabilities
-   Limitations
-   Runtime
-   Provider
-   Permissions
-   Version
-   Availability
-   Status

سیستم باید بتواند Agentهای جدید را بدون تغییر اساسی در هسته ثبت کند.

## انواع Agent

1.  Internal Agent
2.  External Agent
3.  Human-assisted Agent

هر سه نوع باید از قراردادهای مشترک ورودی و خروجی استفاده کنند.

# 7. Task Management

Task Manager مسئول چرخه عمر Taskها است.

هر Task باید شامل موارد زیر باشد:

-   Task ID
-   Title
-   Description
-   Input
-   Expected Output
-   Assigned Agent
-   Priority
-   Dependencies
-   Constraints
-   Acceptance Criteria
-   Status
-   Created At
-   Updated At

## Task Lifecycle

`CREATED → PLANNED → READY → ASSIGNED → RUNNING → REVIEW → COMPLETED`

وضعیت‌های جانبی:

-   BLOCKED
-   FAILED
-   CANCELLED
-   CHANGES_REQUESTED
-   WAITING_FOR_APPROVAL

تأیید انسانی برای تمام Taskها اجباری نیست. Policy Engine مشخص می‌کند کدام
Taskها به Approval نیاز دارند.

# 8. Hybrid Execution Architecture

سیستم باید سه روش اجرای وظایف را پشتیبانی کند.

## A. Internal Execution

Agent داخل Runtime سیستم اجرا می‌شود؛ مانند Python Agent، Code Analysis
Agent، Testing Agent و Documentation Agent.

## B. External Execution

وظیفه توسط Agent یا سرویس بیرونی انجام می‌شود؛ مانند ChatGPT،
GitHub-based Agents و External AI Providers.

## C. Human-assisted Execution

در برخی مراحل انسان بخشی از اجرای کار را بر عهده می‌گیرد؛ مانند بررسی
تصمیم معماری، تأیید تغییر حساس، اجرای دستی یک مرحله یا بازبینی خروجی
Agent.

تمام روش‌ها باید از Execution Contract و Result Contract مشترک استفاده
کنند.

# 9. Policy Engine و Approval

هدف سیستم خودکارسازی عملیات است، نه متوقف‌کردن دائمی کار برای دریافت
تأیید.

Policy Engine باید براساس موارد زیر تصمیم بگیرد:

-   سطح ریسک.
-   سطح دسترسی Agent.
-   نوع عملیات.
-   محدوده تغییرات.
-   قابلیت بازگشت عملیات.
-   حساسیت اطلاعات.
-   Policy تعریف‌شده توسط کاربر.

اصول:

1.  عملیات استاندارد و از پیش مجازشده بدون تأیید اضافی انجام می‌شوند.
2.  عملیات کم‌ریسک در محدوده مجوزها خودکار هستند.
3.  عملیات حساس یا مخرب طبق Policy به Approval نیاز دارند.
4.  عملیات خارج از محدوده مجاز متوقف می‌شوند.
5.  تمام تصمیمات و تأییدها ثبت می‌شوند.

نمونه عملیات نیازمند بررسی ویژه:

-   حذف غیرقابل بازگشت داده‌ها.
-   انتشار یا Deployment حساس.
-   تغییرات امنیتی مهم.
-   تغییرات خارج از محدوده دسترسی.
-   اقداماتی که تصمیم انسانی ضروری دارند.

# 10. Database و استقلال Target

هر Target دارای Database مستقل است.

اطلاعات اصلی سیستم شامل:

-   Agents
-   Tasks
-   Executions
-   Events
-   Results
-   Approvals
-   Project Context
-   Configuration
-   History

Database داخلی Target منبع اصلی وضعیت سیستم است.

GitHub Issues، Pull Requests و GitHub Actions ابزارهای Integration هستند
و منبع اجباری حقیقت سیستم محسوب نمی‌شوند.

برای MVP استفاده از SQLite مناسب است. معماری باید امکان انتقال به
PostgreSQL را در آینده حفظ کند.

# 11. Contracts

تمام اجزای سیستم باید براساس قراردادهای مشخص با یکدیگر ارتباط برقرار
کنند.

قراردادهای اصلی:

1.  Agent Contract
2.  Task Contract
3.  Message Contract
4.  Execution Contract
5.  Result Contract
6.  Event Contract

این قراردادها باید به‌صورت Schema رسمی تعریف شوند.

پیشنهاد اولیه:

-   Pydantic Models
-   JSON Schema
-   Versioned Contracts

تغییر قراردادها باید با Versioning و سازگاری نسخه‌ها مدیریت شود.

# 12. ساختار پیشنهادی داخل Target

مسیر اختصاصی V2:

`.agent-system/`

ساختار پیشنهادی:

``` text
target-repository/
├── .agent-system/
│   ├── VERSION
│   ├── INSTALLATION
│   ├── config/
│   ├── core/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── events/
│   │   └── policies/
│   ├── agents/
│   │   ├── registry/
│   │   ├── profiles/
│   │   └── capabilities/
│   ├── orchestration/
│   │   ├── alpha/
│   │   ├── planner/
│   │   ├── dispatcher/
│   │   └── scheduler/
│   ├── task_manager/
│   ├── runtime/
│   │   ├── interfaces/
│   │   ├── internal/
│   │   ├── external/
│   │   └── workers/
│   ├── integrations/
│   │   ├── providers/
│   │   ├── repositories/
│   │   └── adapters/
│   ├── interfaces/
│   │   ├── cli/
│   │   └── api/
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── logging/
│   │   └── security/
│   ├── data/
│   ├── context/
│   ├── history/
│   ├── artifacts/
│   ├── logs/
│   └── tests/
├── src/
├── tests/
├── docs/
└── README.md
```

این ساختار مبنای طراحی است و جزئیات آن هنگام پیاده‌سازی براساس مرزبندی
واقعی ماژول‌ها نهایی می‌شود.

داده‌های عملیاتی، Cache، Logs و Secrets نباید به‌صورت ناخواسته وارد Git
شوند. تنظیمات اشتراکی، قراردادها و مستندات معماری می‌توانند Version
Controlled باشند. Secrets باید خارج از فایل‌های عمومی Repository نگهداری
شوند.

# 13. Technology Stack پیشنهادی

  بخش                  فناوری پیشنهادی
  -------------------- -----------------------
  Core                 Python
  API                  FastAPI
  Data Validation      Pydantic
  Database             SQLite / PostgreSQL
  ORM                  SQLAlchemy
  Migration            Alembic
  Queue                Database-backed Queue
  Runtime              Python Workers
  Communication        HTTP / Events
  Integration          Adapter Architecture
  Testing              Pytest
  Service Management   systemd (Optional)
  Documentation        Markdown

انتخاب فناوری‌ها باید Free-first باشد. سیستم نباید برای عملکرد پایه به
API پولی وابسته باشد.

AI Provider باید از هسته سیستم جدا باشد تا Provider یا Runtime جدید بدون
بازنویسی Core قابل اضافه‌شدن باشد.

ChatGPT در حالت مکالمه معمولی الزاماً API قابل فراخوانی در اختیار سیستم
قرار نمی‌دهد. بنابراین Manual Handoff و GitHub-based Handoff باید در
معماری External Execution پیش‌بینی شوند.

# 14. چرخه استاندارد مدیریت پروژه

پس از Handoff، Local Alpha درخواست‌های کاربر را مدیریت می‌کند.

چرخه اصلی:

`INTAKE → CONTEXT → AUDIT → PLAN → APPLY → VERIFY → REPORT`

شرح:

-   INTAKE: دریافت درخواست.
-   CONTEXT: دریافت اطلاعات مرتبط پروژه.
-   AUDIT: بررسی وضعیت موجود.
-   PLAN: طراحی مراحل اجرا.
-   APPLY: اجرای تغییرات مجاز.
-   VERIFY: تست و اعتبارسنجی.
-   REPORT: ارائه نتیجه.

این چرخه به معنی درخواست Approval در هر مرحله نیست. اجرای عملیات طبق
Policy و سطح مجوز انجام می‌شود.

# 15. مدیریت Context و Knowledge

سیستم باید سه نوع دانش را مدیریت کند.

## Project Knowledge

اطلاعات مربوط به پروژه Target:

-   Architecture
-   Requirements
-   Decisions
-   Documentation
-   Constraints
-   Current Status

## Agent Knowledge

اطلاعات مربوط به Agentها:

-   Capabilities
-   Limitations
-   Instructions
-   Previous Performance

## Execution Knowledge

اطلاعات مربوط به اجرا:

-   Task History
-   Execution Results
-   Errors
-   Lessons Learned
-   Artifacts

Context باید قابل بازیابی باشد و وابستگی به Conversation خاص نداشته
باشد.

# 16. امنیت و جداسازی

اصول امنیتی:

1.  هر Target فقط به داده‌های خودش دسترسی دارد.
2.  Agentها فقط در محدوده Permissions خود فعالیت می‌کنند.
3.  Secrets در Git ذخیره نمی‌شوند.
4.  عملیات حساس ثبت و قابل پیگیری هستند.
5.  دسترسی به فایل‌ها و اجرای Commandها محدود می‌شود.
6.  اجرای External Agentها از طریق Adapterهای کنترل‌شده انجام می‌شود.
7.  عملیات مخرب یا غیرقابل بازگشت تحت Policy ویژه قرار می‌گیرند.

# 17. Roadmap توسعه

## P0 --- Architecture & Specification

-   تثبیت معماری.
-   نهایی‌سازی Contracts.
-   تعریف Installation Lifecycle.
-   تعریف Role Transition.
-   تعیین ساختار پروژه.

## P1 --- Foundation

-   Core Domain.
-   Configuration.
-   Database.
-   Logging.
-   Event System.
-   Installer.

## P2 --- Agent Management

-   Agent Registry.
-   Agent Profiles.
-   Capabilities.
-   Permissions.

## P3 --- Task Orchestration

-   Task Manager.
-   Planner.
-   Dispatcher.
-   Scheduler.
-   Task Lifecycle.

## P4 --- Hybrid Runtime

-   Internal Runtime.
-   External Runtime.
-   Human-assisted Execution.
-   Result Processing.

## P5 --- Coordination

-   Agent Communication.
-   Event Handling.
-   Execution Coordination.
-   Retry & Error Handling.

## P6 --- Knowledge & Monitoring

-   Project Context.
-   History.
-   Artifacts.
-   Monitoring.
-   Audit Trail.

## P7 --- Validation & Release

-   Installation Tests.
-   Integration Tests.
-   End-to-End Tests.
-   Upgrade Tests.
-   Documentation.
-   Release.

# 18. MVP --- Minimum Viable Product

اولین نسخه قابل استفاده باید حداقل امکانات زیر را داشته باشد:

1.  نصب مستقل V2 داخل Target.
2.  Installer Alpha.
3.  Role Transition به Local Alpha.
4.  Local Alpha.
5.  Agent Registry.
6.  Task Manager.
7.  Database مستقل.
8.  Internal Runtime.
9.  External/Human Handoff.
10. Project Context.
11. Execution History.
12. Basic CLI.
13. Policy Engine اولیه.
14. چرخه Audit، Plan، Apply و Verify.
15. Installation Verification.

Dashboard پیشرفته، Multi-Provider Automation و Pluginهای پیچیده در مراحل
بعدی توسعه قرار می‌گیرند.

# 19. معیارهای پذیرش (Acceptance Criteria)

-   [ ] V2 مستقل از V1 باشد.
-   [ ] V1 بدون تغییر باقی بماند.
-   [ ] Source Repository بسته کامل و قابل نصب ارائه کند.
-   [ ] Installer Alpha بتواند Source و Target را دریافت کند.
-   [ ] Installer Alpha نصب قبلی را تشخیص دهد.
-   [ ] در نبود نصب قبلی، V2 به‌صورت خودکار نصب شود.
-   [ ] نصب مجدد باعث حذف داده‌های قبلی نشود.
-   [ ] نصب و بارگذاری نسخه موجود Verify شود.
-   [ ] Role Transition در همان Conversation انجام شود.
-   [ ] Local Alpha مدیریت پروژه را بر عهده بگیرد.
-   [ ] Target بدون وابستگی عملیاتی به Source کار کند.
-   [ ] هر Target Database و Context مستقل داشته باشد.
-   [ ] Agentها از طریق Contracts استاندارد ارتباط برقرار کنند.
-   [ ] اجرای Internal، External و Human-assisted پشتیبانی شود.
-   [ ] Approvalها براساس Policy باشند.
-   [ ] تاریخچه عملیات قابل بازیابی باشد.
-   [ ] سیستم قابلیت Upgrade کنترل‌شده داشته باشد.

# 20. اصول غیرقابل نقض طراحی

1.  استقلال کامل V2 از V1.
2.  استقلال عملیاتی هر Target.
3.  Repository-Embedded Architecture.
4.  جداسازی Installer Alpha از Local Alpha از نظر Role و مسئولیت.
5.  انجام Role Transition در همان Conversation.
6.  عدم وابستگی روزمره به Source Repository.
7.  عدم حذف اطلاعات موجود هنگام نصب یا Upgrade.
8.  عدم اجبار Approval برای عملیات استاندارد و مجاز.
9.  استفاده از Contracts استاندارد.
10. قابلیت توسعه بدون وابستگی به یک Provider یا Runtime.
11. نگهداری وضعیت واقعی سیستم در Database داخل Target.
12. حفظ Traceability و تاریخچه عملیات.

------------------------------------------------------------------------

# نتیجه نهایی

Agent Management System V2 یک سیستم مدیریتی مستقل است که داخل هر Target
Repository نصب می‌شود و مدیریت همان پروژه را بر عهده می‌گیرد.

چرخه شروع به کار:

`Source Repository → Installer Alpha → Target Repository → Detect / Install → Verify → Role Transition → Local Alpha`

پس از انتقال نقش:

`User → Local Alpha → Task Manager → Agent Registry → Execution Runtime → Result Processing → Verification → User`

**Installer Alpha مسئول آماده‌سازی محیط است. Local Alpha مسئول مدیریت
پروژه است.**

این سند مبنای رسمی طراحی و توسعه V2 خواهد بود.

------------------------------------------------------------------------

# 21. تصمیم‌های اجرایی نسخه 1.1

تاریخ بازنگری: 2026-10-30

این فصل ابهام‌های اجرایی فصل‌های پیشین را رفع می‌کند. در تعارض درباره محدوده MVP، ترتیب ساخت، ساختار نصب یا جزئیات اجرا، فصل‌های 21 تا 25 مقدم هستند. اصول استقلال V2، حفظ داده و Repository-Embedded Architecture برقرار می‌مانند. نسخه سند با نسخه Release نرم‌افزار مستقل است؛ این سند به معنی آماده‌بودن نرم‌افزار نیست.

## 21.1 تعریف عملی Alpha

Installer Alpha و Local Alpha دو Role یک Agent در Conversation هستند. عملیات نصب و مدیریت توسط CLI و Application Services قطعی انجام می‌شود؛ AI از ابزارها یا Manual Handoff استفاده می‌کند. Local Alpha به معنی وجود دائمی یک Process هوشمند در پس‌زمینه نیست.

تغییر Role در همان Conversation مسیر اصلی است. چون کنترل Conversation متعلق به محیط میزبان است، سیستم باید در Conversation جدید هم با خواندن Manifest، Database و Context مدیریت پروژه را بازیابی کند. Conversation منبع حقیقت نیست. Handoff شامل installation_id، target identity، نسخه، آخرین Verify، درخواست جاری، Taskهای باز و اقدام بعدی است و Secrets را منتقل نمی‌کند.

حالت پایه بدون API پولی شامل نصب، مدیریت Task، Worker قطعی و Manual Handoff است. برنامه‌ریزی هوشمند خودکار نیازمند Provider قابل دسترس است. در MVP، Planner دستی یا مبتنی بر Template کافی است؛ استفاده مستقیم از اشتراک مکالمه‌ای به‌عنوان API فرض نمی‌شود.

## 21.2 نصب و بسته توزیع

Installer به محیط اجرای واقعی، Checkout محلی و مجوز لازم نیاز دارد. URL به‌تنهایی تضمین دسترسی نیست. Preflight باید Git، مسیر Target، مجوز نوشتن، وضعیت Working Tree و Dependencies را بررسی کند. تغییرات نامرتبط موجود حفظ شوند؛ Install خودش Commit یا Push نمی‌کند.

ساختار Source:

```text
agent-management-system-v2/
  pyproject.toml
  src/agent_system/
    domain/
    application/
    contracts/
    orchestration/
    runtime/
    integrations/
    infrastructure/
    interfaces/
  migrations/
  install/
  templates/
  tests/unit/
  tests/integration/
  tests/e2e/
  docs/adr/
  .github/workflows/
```

ساختار Target:

```text
.agent-system/
  manifest.json
  app/
  config/
  profiles/
  context/shared/
  state/
    system.db
    context/private/
    artifacts/
    logs/
  .venv/
```

`app/` بسته کامل Release شامل کد و Migration است. Dependencyهای اجرا در محیط محلی آماده می‌شوند. Source code، Manifest، Profileها و Config اشتراکی قابل Version Control هستند. کل state/، .venv/ و Secrets باید Ignore شوند. Context خصوصی زیر state/ قرار می‌گیرد. تنها داده مناسب اشتراک وارد context/shared/ شود.

Manifest حداقل installation_id، release_version، schema_version، source_revision، checksums فایل‌های Release، installation_status و verified_at دارد. نسخه سند، Release و Database Schema مستقل‌اند. شناسه Installation پایدار است؛ Clone یا Restore باید در doctor تشخیص داده شود و هم‌زمان‌سازی State بین Cloneها در MVP پشتیبانی نمی‌شود.

نصب با Lock و Staging انجام می‌شود؛ مراحل قابل تشخیص‌اند و شکست، وضعیت ناقص قابل بازیابی باقی می‌گذارد. نصب دوباره داده را حذف نمی‌کند. فایل تغییرکرده کاربر با Checksum تشخیص داده می‌شود و بی‌صدا Overwrite نمی‌شود. doctor صرفاً وضعیت واقعی را گزارش می‌دهد؛ ناسازگاری نسخه نباید با Load موفق اشتباه گرفته شود.

استقلال عملیاتی یعنی پس از نصب و آماده‌سازی Dependencies، عملیات محلی بدون Source Repository کار می‌کند. سرویس External در صورت انتخاب همچنان به Endpoint خودش نیاز دارد. نصب کاملاً Offline با Dependencies بسته‌بندی‌شده خارج از MVP است.

## 21.3 Upgrade و Recovery

Upgrade اختیاری است و هرگز در Load عادی انجام نمی‌شود. مراحل: Preflight، توقف پذیرش کار جدید، تعیین تکلیف Execution فعال، Backup سازگار SQLite همراه Artifacts و Config مرتبط، Staging Release، بررسی سازگاری، Migration و Verify.

Backup از Database فعال با کپی ساده فایل اصلی انجام نشود؛ از SQLite Backup API یا توقف معتبر Writer استفاده شود. Backup دارای Inventory و Checksum باشد و Restore آزموده شود. در شکست، گزارش و مسیر Recovery ارائه شود. Rollback کد به‌تنهایی Rollback Schema نیست؛ Restore داده ممکن است لازم باشد. تضمین حفظ داده مربوط به داده پیش از Upgrade است و نباید به معنی حفظ Writeهای پس از Backup تعبیر شود.

## 21.4 مرز اجرا و Permissions

استقلال Target یک مرز منطقی است. کنترل مسیر باید Path Traversal و Symlink Escape را پوشش دهد. Policy پیش از اثر عملیات بررسی می‌شود. Secrets در Config فقط به‌صورت Reference هستند و در Logs و Handoff ثبت نمی‌شوند.

در MVP اجرای Internal به Workerهای مشخص و مورد اعتماد محدود است. اجرای کد نامطمئن با subprocess، Timeout یا بررسی Path به‌تنهایی Sandbox نیست. اجرای کد نامطمئن، Network Isolation سخت و Container Sandbox عمومی به مرحله بعد منتقل می‌شود. Runtime محدودیت واقعی خود را در قابلیت‌ها اعلام می‌کند و اگر Permission قابل اعمال نباشد عملیات رد می‌شود.

# 22. Contracts و State Management

همه Contracts دارای schema_version هستند. Timestampها در UTC و شناسه‌ها پایدارند. Task هدف منطقی است؛ Execution هر Attempt اجرای آن است.

| Contract | فیلدهای تکمیلی الزامی |
| --- | --- |
| Task | revision، verification_spec، dependency_ids |
| Execution | execution_id، task_id، attempt، timeout_seconds، heartbeat_at، lease_expires_at، idempotency_key |
| Result | result_id، execution_id، status، artifacts، error_code، retryable |
| Event | event_id، event_type، occurred_at، correlation_id، causation_id، payload |
| Approval | approval_id، action_digest، scope، expires_at، decided_by، decision |
| Artifact | artifact_id، execution_id، relative_path، size_bytes، checksum |

Acceptance Criteria انسانی باید از verification_spec قابل اجرا جدا شود. نتیجه Agent ادعای موفقیت است؛ Task تنها پس از Verify موفق COMPLETED می‌شود. Verifier و شواهد نتیجه باید ثبت شوند.

## 22.1 انتقال‌های Task

| وضعیت مبدأ | مقصد مجاز | شرط |
| --- | --- | --- |
| CREATED | PLANNED، CANCELLED | برنامه و معیار پذیرش ثبت شده یا لغو شده |
| PLANNED | READY، BLOCKED، CANCELLED | Dependencies و Policy بررسی شوند |
| READY | ASSIGNED، BLOCKED، WAITING_FOR_APPROVAL، CANCELLED | انتخاب Agent یا مانع مشخص |
| ASSIGNED | RUNNING، READY، WAITING_FOR_APPROVAL، CANCELLED | Execution ساخته شود یا تخصیص آزاد شود |
| RUNNING | REVIEW، FAILED، BLOCKED، WAITING_FOR_APPROVAL، CANCELLED | نتیجه یا خطا یا توقف کنترل‌شده ثبت شود |
| REVIEW | COMPLETED، CHANGES_REQUESTED، FAILED، WAITING_FOR_APPROVAL، CANCELLED | Verify یا تصمیم Policy |
| CHANGES_REQUESTED | PLANNED، CANCELLED | بازنگری برنامه |
| BLOCKED | PLANNED، READY، CANCELLED | رفع مانع و ارزیابی مجدد |
| WAITING_FOR_APPROVAL | PLANNED، READY، REVIEW، BLOCKED، CANCELLED | مقصد ذخیره‌شده معتبر و Policy دوباره ارزیابی شود |
| FAILED | PLANNED، CANCELLED | Retry با بودجه باقی‌مانده و Attempt جدید |
| COMPLETED، CANCELLED | بدون انتقال | درخواست جدید یک Task جدید می‌سازد |

Approval تنها از وضعیت بدون اجرای اثر فعال قابل انتظار است؛ ورود از RUNNING نیازمند توقف در Checkpoint است. وضعیت بازگشت، اقدام مورد انتظار و دلیل توقف ذخیره شوند. رد Approval به BLOCKED یا CANCELLED می‌رود و به معنی اجازه اجرا نیست. Dependency چرخه‌ای یا وابستگی به Task ناشناخته رد شود؛ Dependency ناموفق یا لغوشده Task وابسته را BLOCKED می‌کند.

## 22.2 Queue و خطا

Queue دارای at-least-once semantics است. Claim کار و تغییر وضعیت باید Transactional باشند. Heartbeat و Lease، Worker قطع‌شده را قابل تشخیص می‌کنند. Lease منقضی، مالکیت اجرای Worker قدیمی را باطل می‌کند؛ Update و Apply باید Owner Token معتبر داشته باشند. Expiry به‌تنهایی مجوز تکرار اقدام با اثر نامعلوم نیست.

هر Retry یک Execution جدید ایجاد می‌کند. خطای ورودی، Permission و Contract خودکار Retry نمی‌شود. خطای موقت فقط تا سقف Attempts با Backoff قابل Retry است. اثر نامشخص به بررسی نیاز دارد. Idempotency باید در عملیات اثرگذار اعمال شود؛ Exactly-once عمومی وعده داده نمی‌شود.

در MVP تنها یک Writer عملیاتی و یک اجرای تغییردهنده برای هر Target فعال است. Taskهای Read-only می‌توانند در آینده موازی شوند. Git Worktree و Merge هماهنگ برای چند Agent تغییردهنده خارج از MVP است.

Cancellation ابتدا درخواست ثبت می‌کند؛ CANCELLED پس از توقف تأییدشده ثبت می‌شود. نتیجه دیررس، تکراری یا متعلق به Owner قدیمی نباید Task نهایی را بازنویسی کند.

## 22.3 Manual Handoff و Approval

Export دارای handoff_id، execution_id، input_digest، Contract Version، ورودی مجاز و خروجی مورد انتظار است. Import باید شناسه، Schema، ارتباط با Execution، تکراری‌نبودن نتیجه و Inventory فایل‌ها را بررسی کند. Import نتیجه اجازه اجرای Command موجود در متن نتیجه نیست؛ Apply مسیر Policy جداگانه دارد.

Approval به Digest اقدام، محدوده و زمان اعتبار متصل است. تغییر محتوای اقدام، Approval قبلی را برای اقدام جدید نامعتبر می‌کند. تصمیم‌ها با Policy Version و دلیل ثبت شوند. عملیات از پیش مجازشده به Approval تکراری نیاز ندارد.

State و Event مربوط در یک Transaction ثبت شوند. انتشار به سرویس بیرونی در آینده از Transactional Outbox استفاده کند. MVP به Event Bus خارجی نیاز ندارد. تغییر هم‌زمان رکورد با revision کنترل شود.

# 23. محدوده اجرایی MVP

داخل MVP: CLI، Installer، doctor، SQLite و Migration، Contracts، Registry، Task Manager، Template/Manual Planner، Queue ساده، Worker مورد اعتماد، Manual Handoff، Policy اولیه، Context، Events، Artifacts، Backup/Restore و Upgrade آزموده‌شده.

خارج از MVP: Dashboard، API عمومی و سرویس دائمی اجباری، SSH Adapter، GitHub Sync خودکار، Multi-Provider Automation، اجرای کد نامطمئن، چند Writer هم‌زمان، Vector Database، نصب Offline کامل و انتقال اجرایی PostgreSQL.

SQLAlchemy و Alembic برای Storage استفاده شوند؛ Domain به آن‌ها وابسته نباشد. امکان Adapter آینده PostgreSQL حفظ شود ولی پشتیبانی آن بدون آزمون ادعا نشود. Dependencyها در Release قفل شوند؛ نسخه دقیق Python و Dependencies در مرحله Foundation پس از بررسی محیط و سازگاری ثبت شود.

# 24. مراحل پیاده‌سازی و Gates

| مرحله | خروجی | معیار عبور |
| --- | --- | --- |
| 0 | Specification 1.1 و ADRهای Alpha، Distribution، State، Runtime | تصمیم‌های این سند در Repository ثبت شوند |
| 1 | Repository مستقل، pyproject، CLI پایه و CI | نصب روی محیط تمیز و اجرای تست پایه |
| 2 | Contracts، Errors، Permissions و State Machine | ورودی نامعتبر و انتقال نامجاز رد شوند |
| 3 | SQLite، Migration، Events و Config | Restart داده را حفظ کند؛ Transaction ناقص باقی نماند |
| 4 | Install، Detect، Load و doctor | نصب تمیز، نصب مجدد و شکست میانی بدون حذف داده آزموده شوند |
| 5 | مسیر عمودی Registry تا Verify | یک Task واقعی با Worker مشخص اجرا و نتیجه بررسی شود |
| 6 | Lease، Retry، Timeout و Cancellation | قطع Worker، نتیجه دیررس و اثر نامعلوم مدیریت شوند |
| 7 | Manual Handoff و Policy کامل اولیه | Import ناسازگار رد شود؛ Approval دقیق و قابل انقضا باشد |
| 8 | Context و Handoff Alpha | Conversation جدید از State ادامه دهد؛ دو Target مستقل باشند |
| 9 | Backup، Restore، Upgrade و Release | Upgrade ناموفق قابل Recovery باشد؛ Source قطع و اجرای محلی موفق باشد |

مرحله 0 مبنای آغاز کار است و تکمیل کد محسوب نمی‌شود. اولین Milestone قابل نمایش در پایان مرحله 5 است:

`Install → Verify → Register Agent → Create Task → Execute → Validate Result → Report`

CLI پیشنهادی با نام موقت `ams` شامل install، doctor، status، agent register، task create، task show، run، handoff export/import، approval، context، backup، restore و upgrade است. جزئیات Commandها پیش از پیاده‌سازی در Contract CLI ثبت شوند؛ این‌ها Command آماده نصب فعلی نیستند.

# 25. چک‌لیست Release و راه‌اندازی مخزن

- [ ] مخزن جدید مستقل با نام پیشنهادی agent-management-system-v2 ساخته شود؛ V1 تغییر نکند.
- [ ] Owner برابر sina1991 و URL مطابق ابتدای سند است؛ مخزن ایجادشده توسط مالک Public است.
- [ ] سند حاضر در docs/specification.md قرار گیرد و README وضعیت واقعی پروژه را بیان کند.
- [ ] ADRها، CONTRIBUTING و Policy تغییر Contracts ثبت شوند؛ License پیش از توزیع عمومی تعیین شود.
- [ ] CI شامل Unit، Integration و E2E منتخب روی محیط تمیز باشد.
- [ ] تست دو Target، Restart، نصب مجدد، Secret Redaction و Path Escape موفق باشند.
- [ ] تغییرات نامرتبط Working Tree و داده موجود در نصب حفظ شوند.
- [ ] نتیجه نامعتبر، تکراری و دیررس، Task را به‌اشتباه COMPLETED نکند.
- [ ] قطع Source Repository پس از نصب مانع مسیر محلی نباشد.
- [ ] Backup و Restore واقعی و Upgrade ناموفق آزموده شوند.
- [ ] Release شامل نسخه، Dependencies قفل‌شده، Inventory و Checksums باشد.
- [ ] هیچ ادعای Sandbox، Provider یا Database پشتیبانی‌نشده در README نباشد.

## تغییرات نسبت به 1.0

تعریف اجرایی Alpha، بازیابی Conversation، تفکیک Source و Target، Manifest، نصب قابل بازیابی، State Machine، Execution Attempt، Queue Semantics، محدودیت Runtime، Manual Handoff، Approval، محدوده MVP و Gates اجرایی اضافه شد. URL قدیمی از جایگاه Source قطعی حذف شد تا با مخزن جدید جایگزین شود.

**Document End — Version 1.1**
