import os
import shutil
import tempfile
import uuid
from pathlib import Path
import json
import asyncpg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from main import _parse
from src.models import ParserResponse, StudyPlan

load_dotenv()

UPLOAD_DIR = Path(os.environ.get("STUDY_PLAN_UPLOAD_DIR", "uploaded_plans"))
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="NextStep12 AI - Study Plan Parser API",
    description="API for parsing Palestinian University Study Plans from PDFs.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("ADMIN_PANEL_ORIGIN", "")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_admin(x_api_key: str = Header(...)) -> None:
    if x_api_key != os.environ["ADMIN_API_KEY"]:
        raise HTTPException(status_code=403, detail="Unauthorized")


async def persist_extracted_plan(
    major_id: int,
    academic_year: int,
    uploaded_by: int,
    plan: StudyPlan,
    source_pdf_path: str,
    source_pdf_original_name: str,
) -> int:
    """يحفظ نتيجة الاستخراج بحالة extracted فقط — بانتظار المراجعة، ما يلمس study_plan_courses."""
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        university_row = await conn.fetchrow(
            "SELECT d.university_id FROM majors m JOIN deanships d ON m.deanship_id = d.id WHERE m.id = $1",
            major_id,
        )
        if university_row is None:
            raise ValueError(f"major_id={major_id} غير موجود أو بدون deanship مرتبط")

        row = await conn.fetchrow(
            """
            INSERT INTO study_plans
                (major_id, university_id, academic_year, status, source_pdf_path,
                 source_pdf_original_name, raw_extracted_data, uploaded_by)
            VALUES ($1, $2, $3, 'extracted', $4, $5, $6::json, $7)
            RETURNING id
            """,
            major_id, university_row["university_id"], academic_year,
            source_pdf_path, source_pdf_original_name,
            json.dumps(plan.model_dump(mode="python")), uploaded_by,
        )
        return row["id"]
    finally:
        await conn.close()


async def confirm_and_normalize(plan_id: int, confirmed_by: int) -> int:
    """يفكّك raw_extracted_data لصفوف حقيقية، ويعلّم الخطة confirmed."""
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        plan_row = await conn.fetchrow(
            "SELECT major_id, university_id, raw_extracted_data, status FROM study_plans WHERE id = $1",
            plan_id,
        )
        if plan_row is None:
            raise ValueError("study_plans row not found")
        if plan_row["status"] == "confirmed":
            raise ValueError("already confirmed")

        plan = StudyPlan.model_validate_json(plan_row["raw_extracted_data"])
        university_id = plan_row["university_id"]

        course_count = 0
        code_to_spc_id: dict[str, int] = {}
        raw_prereqs: list[tuple[int, str]] = []

        async with conn.transaction():
            for year in plan.years:
                for semester in year.semesters:
                    for course in semester.courses:
                        course_id = await conn.fetchval(
                            """
                            INSERT INTO courses (university_id, code, name_ar, default_total_hours,
                                                  default_theory_hours, default_practical_hours, default_type)
                            VALUES ($1,$2,$3,$4,$5,$6,$7)
                            ON CONFLICT (university_id, code) DO UPDATE SET name_ar = EXCLUDED.name_ar
                            RETURNING id
                            """,
                            university_id, course.course_code, course.course_name_ar,
                            course.credit_hours.total, course.credit_hours.theory, course.credit_hours.practical,
                            course.course_type.value,
                        )
                        spc_id = await conn.fetchval(
                            """
                            INSERT INTO study_plan_courses (study_plan_id, course_id, year_number, semester_number)
                            VALUES ($1,$2,$3,$4)
                            RETURNING id
                            """,
                            plan_id, course_id, year.year_number, semester.semester_number,
                        )
                        code_to_spc_id[course.course_code] = spc_id
                        for prereq_code in course.prerequisites:
                            raw_prereqs.append((spc_id, prereq_code))
                        course_count += 1

            for spc_id, prereq_code in raw_prereqs:
                resolved_id = code_to_spc_id.get(prereq_code)
                await conn.execute(
                    """
                    INSERT INTO study_plan_course_prerequisites
                        (study_plan_course_id, prerequisite_code, prerequisite_study_plan_course_id)
                    VALUES ($1,$2,$3)
                    """,
                    spc_id, prereq_code, resolved_id,
                )

            await conn.execute(
                "UPDATE study_plans SET is_current = false WHERE major_id = $1 AND id != $2",
                plan_row["major_id"], plan_id,
            )
            await conn.execute(
                """
                UPDATE study_plans
                SET status = 'confirmed', is_current = true, confirmed_by = $1, confirmed_at = now()
                WHERE id = $2
                """,
                confirmed_by, plan_id,
            )
        return course_count
    finally:
        await conn.close()


@app.get("/api/health")
def health_check():
    return {"status": "API is running successfully!"}


@app.post("/api/parse", response_model=ParserResponse, dependencies=[Depends(verify_admin)])
async def parse_study_plan(
    file: UploadFile = File(..., description="The PDF file of the study plan"),
    university_id: str = Query(None, description="Force a specific university ID (e.g., ucas_gaza)"),
    strict: bool = Query(False, description="Treat warnings as errors"),
    persist: bool = Query(False, description="Save extraction result to Supabase as 'extracted' (pending review)"),
    major_id: int | None = Query(None, description="Required if persist=true"),
    academic_year: int | None = Query(None, description="Required if persist=true, e.g. 2026"),
    uploaded_by: int | None = Query(None, description="Required if persist=true — your users.id"),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    if persist and (major_id is None or academic_year is None or uploaded_by is None):
        raise HTTPException(status_code=400, detail="major_id, academic_year, and uploaded_by are required when persist=true")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name

    try:
        response = _parse(pdf_path=tmp_path, strict=strict, university_id=university_id)

        if persist and response.success:
            permanent_path = UPLOAD_DIR / f"{major_id}_{academic_year}_{uuid.uuid4().hex}.pdf"
            shutil.copy(tmp_path, permanent_path)
            plan_id = await persist_extracted_plan(
                major_id=major_id, academic_year=academic_year, uploaded_by=uploaded_by,
                plan=response.data, source_pdf_path=str(permanent_path),
                source_pdf_original_name=file.filename,
            )
            response.warnings.append(
                f"تم الحفظ بحالة 'extracted' (study_plans.id={plan_id}) — بانتظار المراجعة، لسا ما ظهرت للطلاب. "
                f"أكّدها عبر POST /api/confirm/{plan_id}"
            )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/confirm/{plan_id}", dependencies=[Depends(verify_admin)])
async def confirm_study_plan(plan_id: int, confirmed_by: int = Query(..., description="Your users.id")):
    try:
        course_count = await confirm_and_normalize(plan_id, confirmed_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"confirmed": True, "courses_inserted": course_count}
