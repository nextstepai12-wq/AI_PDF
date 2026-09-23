"""
Pydantic models — Single source of truth for the output JSON schema.
Supports: دبلوم متوسط, دبلوم مهني, دبلوم متقدم, بكالوريوس
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, field_serializer

class DegreeType(str, Enum):
    DIPLOMA_INTERMEDIATE = "diploma_intermediate"    # دبلوم متوسط
    DIPLOMA_PROFESSIONAL = "diploma_professional"    # دبلوم مهني
    DIPLOMA_ADVANCED = "diploma_advanced"            # دبلوم متقدم
    BACHELOR = "bachelor"                            # بكالوريوس


class CourseType(str, Enum):
    SPECIALIZATION = "specialization"
    COLLEGE = "college"
    UNIVERSITY = "university"


class CreditHours(BaseModel):
    total: int = Field(..., ge=0, description="Total credit hours")
    theory: int = Field(..., ge=0, description="Theory contact hours")
    practical: int = Field(..., ge=0, description="Practical contact hours")


class Course(BaseModel):
    course_code: str
    course_name_ar: str
    credit_hours: CreditHours
    course_type: CourseType
    prerequisites: List[str] = Field(default_factory=list)
    semester_number: int = Field(..., ge=1, le=2)
    year_number: int = Field(..., ge=1, le=5)

    @field_validator("course_code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper().replace(" ", "")

    @field_serializer("course_type", when_used="json")
    @classmethod
    def _serialize_type(cls, value: CourseType) -> str:
        return {
            CourseType.SPECIALIZATION: "تخصص",
            CourseType.COLLEGE: "كلية",
            CourseType.UNIVERSITY: "جامعة",
        }.get(value, str(value))


class SemesterCreditSummary(BaseModel):
    total_credit_hours: int = 0
    total_theory_hours: int = 0
    total_practical_hours: int = 0
    course_count: int = 0


class Semester(BaseModel):
    semester_number: int
    name_ar: str = ""
    year_number: int
    summary: SemesterCreditSummary
    courses: List[Course]


class Year(BaseModel):
    year_number: int
    semesters: List[Semester]


class CreditHoursBreakdown(BaseModel):
    specialization: int = 0
    college: int = 0
    university: int = 0


class ProgramInfo(BaseModel):
    department_ar: str = ""
    specialization_ar: str = ""
    degree_type: DegreeType
    degree_label_ar: str = ""
    total_credit_hours: int = 0
    credit_hours_breakdown: CreditHoursBreakdown = Field(default_factory=CreditHoursBreakdown)


class ApprovalInfo(BaseModel):
    ucas_code: str = ""
    version: str = ""
    approval_date: str = ""


class UniversityInfo(BaseModel):
    detected_id: str = ""           # Internal ID from registry
    name_ar: str = ""
    name_en: str = ""
    college_ar: str = ""
    college_en: str = ""
    institution_type: str = ""      # university | college | community
    section_ar: str = ""


class PlanStatistics(BaseModel):
    total_courses: int = 0
    total_credit_hours: int = 0
    total_theory_hours: int = 0
    total_practical_hours: int = 0
    years_count: int = 0
    semesters_count: int = 0
    specialization_course_count: int = 0
    college_course_count: int = 0
    university_course_count: int = 0


class StudyPlan(BaseModel):
    university: UniversityInfo
    approval: ApprovalInfo
    program: ProgramInfo
    years: List[Year]
    statistics: PlanStatistics


class ParserResponse(BaseModel):
    success: bool
    data: Optional[StudyPlan] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    source_file: str = ""
    parsed_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent, exclude_none=False)