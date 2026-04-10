from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
from autogen_core.models import (
    ModelInfo,
    CreateResult,
    RequestUsage,
)
from autogen_core import CancellationToken

# Defining database credentials

import asyncio
import psycopg2
from google import genai
import os

from dotenv import load_dotenv
load_dotenv()



GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PG_HOST        = os.getenv("PG_HOST", "localhost")
PG_PORT        = int(os.getenv("PG_PORT", 5432))
PG_DB          = os.getenv("PG_DB")
PG_USER        = os.getenv("PG_USER")
PG_PASSWORD    = os.getenv("PG_PASSWORD")
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)



print("Config loaded successfully")

# ── paste your existing imports and setup here ──────────────────────────────
# from your notebook:
#   GeminiChatClient, ExecutorChatClient, execute_ddl, get_connection
#   classifier, translator, pre_executor, executor, self_corrector, validator
#   run_migration()
# ────────────────────────────────────────────────────────────────────────────

# Connecting to db

def get_connection():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        dbname=PG_DB, user=PG_USER, password=PG_PASSWORD
    )

def execute_ddl(sql: str) -> str:

    try:
        conn = get_connection()
        conn.autocommit = True          # critical for DDL
        cur = conn.cursor()
        cur.execute(sql)
        cur.close()
        conn.close()
        return "SUCCESS"
    except Exception as e:
        return f"ERROR: {str(e)}"
    
# Quick sanity check
test = execute_ddl("SELECT 1")          # lightweight connectivity test
print("DB connection:", test)



class GeminiChatClient:
    def __init__(self):
        self.model_info = ModelInfo(
            vision=False,
            function_calling=False,
            json_output=False,
            family="unknown",
            structured_output=False,
        )

    @property
    def capabilities(self):
        return self.model_info

    async def create(self, messages, **kwargs) -> CreateResult:
        parts = []
        for m in messages:
            if hasattr(m, "content"):
                content = m.content
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for item in content:
                        if hasattr(item, "text"):
                            parts.append(item.text)
        prompt = "\n".join(parts)

        response = gemini_client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=prompt,
        )
        text = response.text.strip()

        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

        return CreateResult(
            content=text,
            usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
            finish_reason="stop",
            cached=False,
        )

    def count_tokens(self, messages, **kwargs):
        return 0

    def remaining_tokens(self, messages, **kwargs):
        return 10000


class ExecutorChatClient:
    def __init__(self):
        self.model_info = ModelInfo(
            vision=False,
            function_calling=False,
            json_output=False,
            family="unknown",
            structured_output=False,
        )

    @property
    def capabilities(self):
        return self.model_info

    async def create(self, messages, **kwargs) -> CreateResult:
        ddl = ""
        for m in reversed(messages):
            if hasattr(m, "content") and isinstance(m.content, str):
                ddl = m.content
                break

        result = execute_ddl(ddl)

        return CreateResult(
            content=result,
            usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
            finish_reason="stop",
            cached=False,
        )

    def count_tokens(self, messages, **kwargs):
        return 0

    def remaining_tokens(self, messages, **kwargs):
        return 10000


print("Clients are ready")

from autogen_agentchat.agents import AssistantAgent

# Object classifier agent

classifier = AssistantAgent(
    name="Classifier",
    model_client=GeminiChatClient(),
    system_message="""
You are a SQL Server object type classifier.
Given any SQL Server DDL snippet, output ONLY a JSON object on a single line.

Rules:
- Detect the primary object type from: TABLE, STORED_PROCEDURE, FUNCTION_SCALAR,
  FUNCTION_TABLE_VALUED, TRIGGER, VIEW
- Extract the object name and (for triggers) the target table name.

Output format (exactly, no extra text):
{"type": "TABLE", "name": "StaffMembers", "target_table": null}
{"type": "TRIGGER", "name": "trg_salary_change", "target_table": "StaffMembers"}
{"type": "STORED_PROCEDURE", "name": "GetActiveStaff", "target_table": null}

Output ONLY the JSON line. Nothing else.
""",
)

print("Classifier agent initiated")

# Translator agent

translator = AssistantAgent(
    name="Translator",
    model_client=GeminiChatClient(),
    system_message="""
You are a SQL Server to PostgreSQL migration expert.
You will receive the SQL Server code prefixed with a classification tag like:
  [OBJECT TYPE: TRIGGER | name: trg_salary_change | target_table: StaffMembers]

Apply ONLY the rules for that object type. Ignore all other sections.

== TABLE ==
- IDENTITY(1,1)       → GENERATED ALWAYS AS IDENTITY
- NVARCHAR(n)         → VARCHAR(n),  NVARCHAR(MAX) → TEXT
- DATETIME            → TIMESTAMP,   GETDATE()     → NOW()
- MONEY               → NUMERIC(19,4)
- BIT                 → BOOLEAN,  default 1 → TRUE,  default 0 → FALSE
- Remove [ ] brackets

== STORED_PROCEDURE ==
- CREATE PROCEDURE          → CREATE OR REPLACE PROCEDURE
- @param_name TYPE          → IN param_name TYPE  (in signature)
- AS BEGIN…END              → LANGUAGE plpgsql AS $$ BEGIN…END $$
- Remove SET NOCOUNT ON
- PRINT 'x'                 → RAISE NOTICE 'x'
- ISNULL(x,y)               → COALESCE(x,y)
- @@ROWCOUNT                → GET DIAGNOSTICS n = ROW_COUNT
- Prefix all parameter names with p_ to avoid column name collisions
  e.g. IN p_DeptID INT, then use p_DeptID in the body
- Apply TABLE data type rules


== FUNCTION_SCALAR ==
- CREATE FUNCTION           → CREATE OR REPLACE FUNCTION
- Remove @ prefix from params
- Keep RETURNS <type>; wrap body in $$ … $$ LANGUAGE plpgsql
- str1 + str2               → str1 || str2
- Prefix all parameter names with p_ to avoid column name collisions
  e.g. IN p_DeptID INT, then use p_DeptID in the body
- Apply TABLE data type rules

== FUNCTION_TABLE_VALUED ==
- Same as FUNCTION_SCALAR header rules
- RETURNS TABLE AS RETURN(…) → RETURNS TABLE(col type, …) with RETURN QUERY
- Prefix all parameter names with p_ to avoid column name collisions
  e.g. IN p_DeptID INT, then use p_DeptID in the body
- Apply TABLE data type rules

== TRIGGER ==
- Split into TWO objects:
  1. CREATE OR REPLACE FUNCTION <name>_fn() RETURNS TRIGGER LANGUAGE plpgsql AS $$
       BEGIN
         … body (INSERTED→NEW, DELETED→OLD, IF UPDATE(col)→IF NEW.col<>OLD.col) …
         RETURN NEW;
       END; $$;
  2. CREATE TRIGGER <name>
       AFTER INSERT OR UPDATE OR DELETE ON <target_table>
       FOR EACH ROW EXECUTE FUNCTION <name>_fn();
- Apply TABLE data type rules

== VIEW ==
- CREATE VIEW               → CREATE OR REPLACE VIEW
- Remove WITH SCHEMABINDING
- Remove WITH (NOLOCK)
- Remove dbo. prefixes
- TOP n                     → LIMIT n
- ISNULL(x,y)               → COALESCE(x,y)
- Apply TABLE data type rules

Return ONLY the converted SQL. No explanations. No markdown fences.
""",
)

print("Translator agent initiated")

# Pre executor for dropping objects before executing

pre_executor = AssistantAgent(
    name="PreExecutor",
    model_client=GeminiChatClient(),
    system_message="""
You are a PostgreSQL cleanup helper.
You will receive a classification tag followed by PostgreSQL DDL, like:
  [OBJECT TYPE: STORED_PROCEDURE | name: GetActiveStaff]

  CREATE OR REPLACE PROCEDURE GetActiveStaff ...

=== CRITICAL RULES ===
1. ONLY generate DROP statements for the EXACT object type in the [OBJECT TYPE] tag.
2. NEVER drop or recreate any other object types not mentioned in the tag.
3. NEVER add any CREATE statements that are not already in the input SQL.
4. ONLY prepend the DROP statement(s). Leave the rest of the SQL completely untouched.
======================

DROP statement to prepend by object type:

- TABLE:
    DROP TABLE IF EXISTS <name> CASCADE;
    (if multiple tables, drop child/dependent tables first, then parent)

- STORED_PROCEDURE:
    DROP PROCEDURE IF EXISTS <name>(<arg types>) CASCADE;

- FUNCTION_SCALAR or FUNCTION_TABLE_VALUED:
    DROP FUNCTION IF EXISTS <name>(<arg types>) CASCADE;

- TRIGGER:
    DROP TRIGGER IF EXISTS <name> ON <target_table>;
    DROP FUNCTION IF EXISTS <name>_fn() CASCADE;
    (always drop trigger before its function)

- VIEW:
    DROP VIEW IF EXISTS <name>;

Output format (strictly follow this):
  <DROP statement(s) for the tagged type only>
  <blank line>
  <original input SQL, completely unchanged>

Return ONLY this. No explanations. No markdown fences. No extra CREATE statements.
""",
)

print("Pre-executor agent initiated")

# Executor agent

executor = AssistantAgent(
    name="Executor",
    model_client=ExecutorChatClient(),
    system_message="Execute the given PostgreSQL DDL and return SUCCESS or the full error message.",
)

print("Executor agent initiated")

# Self corrector agent

self_corrector = AssistantAgent(
    name="SelfCorrector",
    model_client=GeminiChatClient(),
    system_message="""
You are a PostgreSQL expert who fixes broken SQL.
You will receive a classification tag, the broken code, and the error message.

Apply ONLY the fix strategies for the classified type:

== TABLE ==
- Add IF NOT EXISTS if duplicate table error
- Remove FK constraint if referenced table doesn't exist yet
- Fix CHECK constraint column names

== STORED_PROCEDURE ==
- Fix $$ … $$ block syntax
- Fix IN parameter declarations
- Add missing LANGUAGE plpgsql

== FUNCTION_SCALAR / FUNCTION_TABLE_VALUED ==
- Fix RETURNS type mismatch
- Add missing RETURN / RETURN QUERY
- Fix $$ delimiter issues

== TRIGGER ==
- Ensure BOTH the trigger function AND CREATE TRIGGER are present
- Add missing RETURN NEW at end of trigger function
- Use EXECUTE FUNCTION (not EXECUTE PROCEDURE) for Postgres 14+
- Fix function name mismatch between CREATE TRIGGER and the function definition

== VIEW ==
- Fix column ambiguity (add table aliases)
- Remove any remaining dbo. or [bracket] syntax

Return ONLY the corrected SQL. No explanations. No markdown fences.
""",
)

print("Self-corrector agent initiated")

# Validator agent

validator = AssistantAgent(
    name="Validator",
    model_client=GeminiChatClient(),
    system_message="""
You are a PostgreSQL code reviewer.
You will receive a classification tag and the SQL to validate.

Check ONLY the rules for the classified type:

== ALL TYPES (always check) ==
- No SQL Server remnants: IDENTITY, NVARCHAR, DATETIME, GETDATE, ISNULL, NOLOCK, SCHEMABINDING, dbo.
- No square brackets [ ] around identifiers

== TABLE ==
- Correct PG data types, GENERATED ALWAYS AS IDENTITY if needed

== STORED_PROCEDURE ==
- $$ … $$ LANGUAGE plpgsql block present
- Parameters use IN keyword, no @ prefixes
- No SET NOCOUNT ON

== FUNCTION_SCALAR / FUNCTION_TABLE_VALUED ==
- Explicit RETURNS type declared
- LANGUAGE plpgsql present
- TABLE-valued: uses RETURNS TABLE(…) and RETURN QUERY

== TRIGGER ==
- Trigger function present with RETURNS TRIGGER
- Ends with RETURN NEW or RETURN OLD
- CREATE TRIGGER uses EXECUTE FUNCTION (not EXECUTE PROCEDURE)
- Both objects (function + trigger) are present

== VIEW ==
- No SCHEMABINDING, NOLOCK, or dbo. remaining

IMPORTANT:
- If all checks pass → reply with exactly: VALID
- If any check fails → reply with exactly: INVALID: <specific reason>
- Do NOT say VALID or INVALID anywhere in your reasoning — only in your final answer
""",
)

print("Validator agent initiated")


async def run_migration(sql_server_code: str, max_retries: int = 3) -> str | None:
    print("=" * 55)
    print("  SQL to Postgres Pipeline  (v2)")
    print("=" * 55)

    # STEP 1: Classify
    print("\n[1] Classifying object type...")
    result = await classifier.run(task=sql_server_code)
    raw_tag = result.messages[-1].content.strip()
    print(f"    Classification: {raw_tag}")

    try:
        meta = json.loads(raw_tag)
        obj_type   = meta.get("type", "UNKNOWN")
        obj_name   = meta.get("name", "unknown")
        target_tbl = meta.get("target_table") or ""
        type_tag   = (
            f"[OBJECT TYPE: {obj_type} | name: {obj_name}"
            + (f" | target_table: {target_tbl}" if target_tbl else "")
            + "]"
        )
    except json.JSONDecodeError:
        # Graceful fallback if model adds extra text
        type_tag = f"[OBJECT TYPE: UNKNOWN]"
        obj_type = "UNKNOWN"
        print("    Warning: could not parse classification JSON, proceeding without tag.")

    # STEP 2: Translate (with type tag injected)
    print(f"\n[2] Translating ({obj_type})...")
    tagged_input = f"{type_tag}\n\n{sql_server_code}"
    result = await translator.run(task=tagged_input)
    pg_code = result.messages[-1].content.strip()
    print(f"\n    Translated:\n{pg_code}\n")

    # STEP 3: Pre-executor cleanup (auto DROP)
    print("[3] Generating idempotent cleanup prefix...")
    result = await pre_executor.run(task=f"{type_tag}\n\n{pg_code}")
    pg_code_with_drops = result.messages[-1].content.strip()
    print(f"\n    With DROPs:\n{pg_code_with_drops}\n")

    current_code = pg_code_with_drops

    # STEP 4+5: Execute with type-aware self-correction loop
    for attempt in range(1, max_retries + 1):
        print(f"[4] Executing (attempt {attempt}/{max_retries})...")
        result = await executor.run(task=current_code)
        exec_result = result.messages[-1].content
        print(f"    Result: {exec_result}\n")

        if exec_result.startswith("SUCCESS"):
            break

        if attempt == max_retries:
            print("Migration FAILED — max retries reached.")
            return None

        print("    Execution failed → routing to SelfCorrector...")
        fix_prompt = (
            f"{type_tag}\n\n"
            f"The following PostgreSQL code failed:\n\n{current_code}\n\n"
            f"Error:\n{exec_result}\n\n"
            f"Return only the corrected SQL."
        )
        result = await self_corrector.run(task=fix_prompt)
        current_code = result.messages[-1].content.strip()
        print(f"    Corrected:\n{current_code}\n")

    # STEP 6: Validate (type-scoped)
    print("[5] Validating...")
    result = await validator.run(task=f"{type_tag}\n\n{current_code}")
    validation = result.messages[-1].content.strip()
    print(f"    Validator: {validation}\n")

    if validation.startswith("VALID"):
        print("Migration COMPLETE!")
        return current_code
    else:
        # One more correction pass on validation failure before giving up
        print(f"    Validation issue: {validation} — attempting one final correction...")
        fix_prompt = (
            f"{type_tag}\n\n"
            f"This PostgreSQL code passed execution but failed validation:\n\n{current_code}\n\n"
            f"Validation error: {validation}\n\n"
            f"Return only the corrected SQL."
        )
        result = await self_corrector.run(task=fix_prompt)
        current_code = result.messages[-1].content.strip()

        result = await validator.run(task=f"{type_tag}\n\n{current_code}")
        validation = result.messages[-1].content.strip()
        if validation.startswith("VALID"):
            print("Migration COMPLETE (after post-validation fix)!")
            return current_code
        else:
            print(f"Migration FAILED — validation: {validation}")
            return None


app = FastAPI(title="SQL Migration API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


class MigrateRequest(BaseModel):
    sql: str
    max_retries: int = 3


async def migration_stream(sql: str, max_retries: int):
    """
    Runs the pipeline and yields Server-Sent Events so the React UI
    can show each step in real time as it completes.

    Event shape:  data: {"step": <int>, "label": <str>, "content": <str>, "status": <str>}
    status values: "running" | "ok" | "error" | "done"
    """

    def emit(step: int, label: str, content: str, status: str = "ok") -> str:
        payload = json.dumps({
            "step":    step,
            "label":   label,
            "content": content,
            "status":  status,
        })
        return f"data: {payload}\n\n"

    # ── Step 1: Classify ─────────────────────────────────────────────────────
    yield emit(1, "Classifier", "Detecting object type…", "running")
    try:
        result   = await classifier.run(task=sql)
        raw_tag  = result.messages[-1].content.strip()
        meta     = json.loads(raw_tag)
        obj_type = meta.get("type",  "UNKNOWN")
        obj_name = meta.get("name",  "unknown")
        tgt      = meta.get("target_table") or ""
        type_tag = (
            f"[OBJECT TYPE: {obj_type} | name: {obj_name}"
            + (f" | target_table: {tgt}" if tgt else "")
            + "]"
        )
        yield emit(1, "Classifier", f"{raw_tag}", "ok")
    except Exception as e:
        yield emit(1, "Classifier", f"Classification failed: {e}", "error")
        return

    # ── Step 2: Translate ────────────────────────────────────────────────────
    yield emit(2, "Translator", f"Translating {obj_type}…", "running")
    try:
        result  = await translator.run(task=f"{type_tag}\n\n{sql}")
        pg_code = result.messages[-1].content.strip()
        yield emit(2, "Translator", pg_code, "ok")
    except Exception as e:
        yield emit(2, "Translator", f"Translation failed: {e}", "error")
        return

    # ── Step 3: Pre-executor cleanup ─────────────────────────────────────────
    yield emit(3, "Pre-Executor", "Generating idempotent DROP prefix…", "running")
    try:
        result           = await pre_executor.run(task=f"{type_tag}\n\n{pg_code}")
        pg_code_with_drops = result.messages[-1].content.strip()
        yield emit(3, "Pre-Executor", pg_code_with_drops, "ok")
    except Exception as e:
        yield emit(3, "Pre-Executor", f"Pre-executor failed: {e}", "error")
        return

    current_code = pg_code_with_drops

    # ── Step 4+5: Execute with self-correction loop ──────────────────────────
    for attempt in range(1, max_retries + 1):
        yield emit(4, "Executor", f"Executing (attempt {attempt}/{max_retries})…", "running")
        try:
            result      = await executor.run(task=current_code)
            exec_result = result.messages[-1].content.strip()
        except Exception as e:
            yield emit(4, "Executor", f"Executor error: {e}", "error")
            return

        if exec_result.startswith("SUCCESS"):
            yield emit(4, "Executor", "SUCCESS", "ok")
            break

        yield emit(4, "Executor", exec_result, "error")

        if attempt == max_retries:
            yield emit(4, "Executor", "Max retries reached — migration failed.", "error")
            yield emit(0, "Pipeline", "FAILED", "error")
            return

        # Self-correct
        yield emit(5, "SelfCorrector", "Fixing error…", "running")
        fix_prompt = (
            f"{type_tag}\n\n"
            f"The following PostgreSQL code failed:\n\n{current_code}\n\n"
            f"Error:\n{exec_result}\n\n"
            f"Return only the corrected SQL."
        )
        try:
            result       = await self_corrector.run(task=fix_prompt)
            current_code = result.messages[-1].content.strip()
            yield emit(5, "SelfCorrector", current_code, "ok")
        except Exception as e:
            yield emit(5, "SelfCorrector", f"SelfCorrector error: {e}", "error")
            return

    # ── Step 6: Validate ─────────────────────────────────────────────────────
    yield emit(6, "Validator", "Validating…", "running")
    try:
        result     = await validator.run(task=f"{type_tag}\n\n{current_code}")
        validation = result.messages[-1].content.strip()
    except Exception as e:
        yield emit(6, "Validator", f"Validator error: {e}", "error")
        return

    if validation.startswith("VALID"):
        yield emit(6, "Validator", "VALID", "ok")
        yield emit(0, "Pipeline", current_code, "done")
    else:
        yield emit(6, "Validator", validation, "error")

        # One final correction pass on validation failure
        yield emit(5, "SelfCorrector", "Fixing validation issue…", "running")
        fix_prompt = (
            f"{type_tag}\n\n"
            f"This code passed execution but failed validation:\n\n{current_code}\n\n"
            f"Validation error: {validation}\n\nReturn only the corrected SQL."
        )
        try:
            result       = await self_corrector.run(task=fix_prompt)
            current_code = result.messages[-1].content.strip()
            yield emit(5, "SelfCorrector", current_code, "ok")

            result     = await validator.run(task=f"{type_tag}\n\n{current_code}")
            validation = result.messages[-1].content.strip()
            if validation.startswith("VALID"):
                yield emit(6, "Validator", "VALID", "ok")
                yield emit(0, "Pipeline", current_code, "done")
            else:
                yield emit(6, "Validator", validation, "error")
                yield emit(0, "Pipeline", "FAILED", "error")
        except Exception as e:
            yield emit(5, "SelfCorrector", f"Final correction failed: {e}", "error")


@app.post("/migrate")
async def migrate(req: MigrateRequest):
    return StreamingResponse(
        migration_stream(req.sql, req.max_retries),
        media_type="text/event-stream",
        headers={
            "Cache-Control":  "no-cache",
            "X-Accel-Buffering": "no",      # nginx: disable buffering
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}