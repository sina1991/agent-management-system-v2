from sqlalchemy import Column, Integer, MetaData, String, Table, Text

metadata = MetaData()

tasks = Table("tasks", metadata,
              Column("task_id", String(36), primary_key=True),
              Column("revision", Integer, nullable=False),
              Column("payload", Text, nullable=False))
events = Table("events", metadata,
               Column("sequence", Integer, primary_key=True, autoincrement=True),
               Column("event_id", String(36), unique=True, nullable=False),
               Column("correlation_id", String(36), nullable=False, index=True),
               Column("payload", Text, nullable=False))
configuration = Table("configuration", metadata,
                      Column("key", String, primary_key=True),
                      Column("payload", Text, nullable=False))

executions = Table("executions", metadata,
                   Column("execution_id", String(36), primary_key=True),
                   Column("task_id", String(36), nullable=False, index=True),
                   Column("attempt", Integer, nullable=False),
                   Column("status", String(24), nullable=False, index=True),
                   Column("lease_expires_at", String(40), nullable=False),
                   Column("payload", Text, nullable=False),
                   Column("idempotency_key", String, nullable=False, unique=True))
results = Table("results", metadata,
                Column("result_id", String(36), primary_key=True),
                Column("execution_id", String(36), nullable=False, unique=True),
                Column("status", String(24), nullable=False),
                Column("payload", Text, nullable=False))
