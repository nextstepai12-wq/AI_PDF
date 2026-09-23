import logging
from typing import List
from src.models import StudyPlan, CourseType, PlanStatistics

logger = logging.getLogger(__name__)


def validate_plan(plan: StudyPlan) -> tuple[bool, List[str], List[str]]:
    errors, warnings = [], []
    all_courses, all_codes = [], set()

    for year in plan.years:
        if len(year.semesters) > 2:
            errors.append(f"Year {year.year_number}: {len(year.semesters)} semesters (max 2)")
        for sem in year.semesters:
            if sem.summary.course_count == 0:
                errors.append(f"Y{year.year_number}S{sem.semester_number}: no courses")
            for c in sem.courses:
                all_courses.append(c)
                if c.course_code in all_codes:
                    errors.append(f"Duplicate: {c.course_code}")
                all_codes.add(c.course_code)
                if not c.course_name_ar or len(c.course_name_ar) < 2:
                    errors.append(f"{c.course_code}: empty name")
                if c.credit_hours.total == 0 and c.credit_hours.theory == 0 and c.credit_hours.practical == 0:
                    warnings.append(f"{c.course_code}: all hours zero")
                for prereq in c.prerequisites:
                    if prereq not in all_codes:
                        warnings.append(f"{c.course_code}: prereq {prereq} not seen yet")

    if plan.program.total_credit_hours > 0:
        computed = sum(c.credit_hours.total for c in all_courses)
        if computed != plan.program.total_credit_hours:
            warnings.append(f"Hours mismatch: metadata={plan.program.total_credit_hours}, computed={computed}")

    return len(errors) == 0, errors, warnings


def compute_statistics(plan: StudyPlan) -> PlanStatistics:
    courses = [c for y in plan.years for s in y.semesters for c in s.courses]
    return PlanStatistics(
        total_courses=len(courses),
        total_credit_hours=sum(c.credit_hours.total for c in courses),
        total_theory_hours=sum(c.credit_hours.theory for c in courses),
        total_practical_hours=sum(c.credit_hours.practical for c in courses),
        years_count=len(plan.years),
        semesters_count=sum(len(y.semesters) for y in plan.years),
        specialization_course_count=sum(1 for c in courses if c.course_type == CourseType.SPECIALIZATION),
        college_course_count=sum(1 for c in courses if c.course_type == CourseType.COLLEGE),
        university_course_count=sum(1 for c in courses if c.course_type == CourseType.UNIVERSITY),
    )