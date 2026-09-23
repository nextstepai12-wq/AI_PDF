"""
Palestinian Universities Knowledge Base
"""

from dataclasses import dataclass, field
from typing import Dict, List
"""
Palestinian Universities Knowledge Base
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  ALL KNOWN COURSE CODE PREFIXES — MUST BE BEFORE DEFAULT_RULES
# ═══════════════════════════════════════════════════════════════

ALL_PREFIXES = [
    # UCAS system (colleges)
    "DINF", "ISSE", "SYBS", "COMP", "UNID", "UNIV", "DIPL",
    # Computing & IT
    "CS", "CSC", "CSCI", "COMP", "CIS",
    "IS", "INFO", "IT", "ISM",
    "SE", "SWE", "SEN",
    "NET", "NW", "NTWK",
    "DB", "DATA", "DBMS",
    "AI", "ML", "DL",
    "SEC", "CYB", "CYS",
    "WEB", "IOS", "AND",
    "OS", "OPS", "SYST",
    "HCI", "GPA",
    # Sciences
    "MATH", "MTH", "CALC", "STAT", "STT",
    "PHYS", "PHY", "PHS",
    "CHEM", "CHM",
    "BIOL", "BIO", "BSC",
    "GEOL", "GEO", "ENV", "SCI",
    # Languages
    "ENGL", "ENG", "EFL", "ESP", "ELT",
    "ARAB", "ARB",
    "FRN", "FRE", "GER", "DEU", "TR", "TUR",
    # Engineering
    "ENGR",
    "CIV", "STR", "CON",
    "ELE", "EE", "ECE",
    "MEC", "ME", "MECH",
    "ARC", "ARCH",
    "SUR", "SURV", "IND", "IE",
    "CHE", "CHEG", "AER", "AE", "BME", "BIOE",
    # Business & Economics
    "MGT", "MGMT", "MNGT", "BUS", "BUSS", "BSAD",
    "ACC", "ACCT",
    "FIN", "FNCE",
    "MKT", "MRKT",
    "ECO", "ECON",
    "ENT", "ENTR",
    "HRM", "HR",
    "MIS", "OM", "SCM", "POM",
    "INS", "INSU", "BAN", "BANK", "TAX",
    "RES", "RESE", "PROJ", "PM",
    # Law & Politics
    "LAW", "LAWC", "POL", "POLS", "IR",
    "PUB", "PADM", "PA", "INTL",
    # Education & Social
    "EDU", "EDUC", "EDP", "CUR", "CURR",
    "PSY", "PSYC", "SOC", "SOCL", "PHI", "PHIL",
    "GEOG", "HIST", "HIS",
    # Health Sciences
    "NUR", "NURS", "PHA", "PHAR", "PHRM",
    "MED", "MD", "DEN", "DNT", "LAB", "LABS",
    "RAD", "RADT", "PT", "PHYT", "EM", "EMS",
    "PHN", "PUBH", "NUT", "FDST", "MLS",
    # Media & Arts
    "COM", "COMM", "MASS", "JOU", "JORN",
    "PR", "PUBR", "ART", "ARTS", "MUS", "MUSC",
    "THE", "THTR", "DES", "DSGN", "GRA", "GRPH",
    "PHO", "PHOT", "VID", "VIDE", "ANI", "ANIM",
    # Agriculture
    "AGR", "AGRI", "AGRN", "HORT", "PLT",
    "ANM", "ANSC", "FOOD", "FDT", "SOS", "SOIL", "PEST",
    # General / University Requirements
    "UNIV", "UNI", "GEN", "GE", "GS", "GSR",
    "SKL", "SKILL", "LIF", "LIFE", "CNT", "COMMU",
    # Sharia & Islamic Studies
    "SHR", "SHAR", "ISL", "ISLM", "QUR", "QURAN",
    "FEQ", "FIQH", "AQD", "AQU", "TAF", "TAFS",
    "HAD", "HADITH",
    # Physical Education
    "PE", "PET", "PES",
]


# ═══════════════════════════════════════════════════════════════
#  University Rules Template
# ═══════════════════════════════════════════════════════════════

@dataclass
class UniversityRules:
    id: str
    name_ar: str
    name_en: str
    institution_type: str
    fingerprints: List[str] = field(default_factory=list)
    degree_patterns: Dict[str, List[str]] = field(default_factory=dict)
    course_type_map: Dict[str, str] = field(default_factory=dict)
    prefixes: List[str] = field(default_factory=list)
    total_hours_pattern: str = ""
    spec_hours_pattern: str = ""
    college_hours_pattern: str = ""
    univ_hours_pattern: str = ""
    ucas_pattern: str = ""
    version_pattern: str = ""
    date_pattern: str = ""
    header_keywords: Dict[str, List[str]] = field(default_factory=dict)
    skip_markers: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
#  Default Fallback Rules
# ═══════════════════════════════════════════════════════════════

DEFAULT_RULES = UniversityRules(
    id="default",
    name_ar="افتراضي",
    name_en="Default",
    institution_type="unknown",
    degree_patterns={
        "diploma_intermediate": ["دبلوم متوسط", "متوسط دبلوم"],
        "diploma_professional": ["دبلوم مهني", "مهني دبلوم", "دبلوم تأهيلي"],
        "diploma_advanced": ["دبلوم متقدم", "دبلوم تأسيسي", "تأسيسي دبلوم"],
        "bachelor": ["بكالوريوس", "بكلوريوس"],
    },
    course_type_map={
        "تخصص": "specialization",
        "اختصاص": "specialization",
        "إجباري تخصص": "specialization",
        "إجباري": "specialization",
        "كلية": "college",
        "جامعة": "university",
        "عامة": "university",
        "حر": "university",
        "انتخابي": "university",
        "مهارات جامعية": "university",
        "مهارات": "university",
    },
    prefixes=ALL_PREFIXES,
    total_hours_pattern=r"(\d+)\s*:\s*الكلي\s*العدد",
    spec_hours_pattern=r"(\d+)\s*:\s*الاختصاص\s*متطلبات",
    college_hours_pattern=r"(\d+)\s*:\s*الكلية\s*متطلبات",
    univ_hours_pattern=r"(\d+)\s*:\s*الجامعة\s*متطلبات",
    ucas_pattern=r"(\d{2,}-\d{2,})\s*UCAS|UCAS\s*(\d{2,}-\d{2,})",
    version_pattern=r"(\d+)\s*الإصدار|الإصدار\s*(\d+)",
    date_pattern=r"(\d{1,2}/\d{1,2}/\d{4})\s*:?\s*التاريخ|التاريخ\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
    header_keywords={
        "course_name":    ["اسم", "المساق اسم", "المادة اسم", "عنوان المساق", "المادة"],
        "course_code":    ["رقم", "المساق رقم", "رمز", "كود", "الرمز", "رقم المساق"],
        "total_hours":    ["معتمدة", "ساعة معتمدة", "معتمدة.س.ع", "المعتمدة", "ساعات معتمدة"],
        "theory_hours":   ["نظرية", "نظري", "نظرية.س.ع", "نظري.س.ع"],
        "practical_hours":["عملية", "عملي", "عملية.س.ع", "عملي.س.ع", "تطبيقي", "تطبيقية"],
        "course_type":    ["نوع", "المساق نوع", "التصنيف", "الفئة", "نوع المساق"],
        "prerequisite":   ["سابقة", "متطلب", "سابقة متطلب", "المتطلب السابق", "السابق"],
    },
    skip_markers=[
        "التوقيع", "العميد", "رئيس", "نائب", "الاسم",
        "المجموع", "إجمالي", "اعتماد", "الإصدار",
        "الدراسية الخطة اعتماد",
    ],
)


# ═══════════════════════════════════════════════════════════════
#  Palestinian University Registry
# ═══════════════════════════════════════════════════════════════

REGISTRY: List[UniversityRules] = [

    # 1. UCAS - غزة
    UniversityRules(
        id="ucas_gaza",
        name_ar="الكلية الجامعية للعلوم التطبيقية",
        name_en="University College of Applied Sciences",
        institution_type="college",
        fingerprints=[
            "الكلية الجامعية للعلوم التطبيقية",
            "University College of Applied Sciences",
            "Sciences Applied of College University",
        ],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط", "متوسط دبلوم"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "تخصص": "specialization",
            "اختصاص": "specialization",
            "كلية": "college",
            "جامعة": "university",
        },
        prefixes=["DINF", "ISSE", "SYBS", "COMP", "UNID", "UNIV", "DIPL",
                   "MATH", "ENGL", "ARAB", "PHYS", "STAT", "COMM"],
        total_hours_pattern=r"(\d+)\s*:\s*الكلي\s*العدد",
        spec_hours_pattern=r"(\d+)\s*:\s*الاختصاص\s*متطلبات",
        college_hours_pattern=r"(\d+)\s*:\s*الكلية\s*متطلبات",
        univ_hours_pattern=r"(\d+)\s*:\s*الجامعة\s*متطلبات",
        ucas_pattern=r"(\d{2,}-\d{2,})\s*UCAS|UCAS\s*(\d{2,}-\d{2,})",
        version_pattern=r"(\d+)\s*الإصدار|الإصدار\s*(\d+)",
    ),

    # 2. بيرزيت
    UniversityRules(
        id="birzeit",
        name_ar="جامعة بيرزيت",
        name_en="Birzeit University",
        institution_type="university",
        fingerprints=["جامعة بيرزيت", "Birzeit University", "بيرزيت"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "اختياري تخصص": "specialization",
            "كلية": "college",
            "إجباري كلية": "college",
            "جامعة": "university",
            "إجباري جامعة": "university",
            "حرة": "university",
            "مهارات جامعية": "university",
        },
        prefixes=["CS", "CIS", "IS", "SE", "IT", "MATH", "PHYS", "CHEM",
                   "ENGL", "ARAB", "STAT", "SOC", "PSY", "PHI", "HIST",
                   "ECON", "MGT", "ACC", "LAW", "EDU", "NUR", "COMM",
                   "MUS", "ART", "DES", "ARCH", "CIV", "ELE", "MEC",
                   "AI", "NET", "DB", "SEC", "WEB", "DATA", "ML"],
    ),

    # 3. النجاح
    UniversityRules(
        id="najah",
        name_ar="جامعة النجاح الوطنية",
        name_en="An-Najah National University",
        institution_type="university",
        fingerprints=["جامعة النجاح", "النجاح الوطنية", "An-Najah", "Najah National"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني", "دبلوم تأهيلي"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "اختياري تخصص": "specialization",
            "كلية": "college",
            "إجباري كلية": "college",
            "جامعة": "university",
            "إجباري جامعة": "university",
            "حرة": "university",
            "انتخابي": "university",
        },
        prefixes=["IT", "CIS", "CS", "SE", "IS", "MATH", "STAT", "PHYS",
                   "CHEM", "BIOL", "ENGL", "ARAB", "ENG", "ECON", "MGT",
                   "ACC", "FIN", "MKT", "LAW", "EDU", "NUR", "PHA",
                   "CIV", "ELE", "MEC", "ARC", "COMM", "SOC", "PSY",
                   "AI", "NET", "SEC", "DATA", "WEB", "DB", "ML",
                   "GE", "GS", "PE"],
    ),

    # 4. القدس
    UniversityRules(
        id="alquds",
        name_ar="جامعة القدس",
        name_en="Al-Quds University",
        institution_type="university",
        fingerprints=["جامعة القدس", "Al-Quds University", "القدس جامعة"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
            "حرة": "university",
            "انتخابي": "university",
        },
        prefixes=["COMP", "CSCI", "CS", "IS", "IT", "SE", "MATH", "STAT",
                   "PHYS", "CHEM", "BIOL", "ENGL", "ARAB", "ENG",
                   "ECON", "MGT", "ACC", "LAW", "EDU", "NUR", "PHA",
                   "CIV", "ELE", "MEC", "MED", "DENT", "COMM",
                   "AI", "NET", "SEC", "DATA", "WEB", "DB",
                   "SHAR", "ISLM", "QUR", "FEQ", "UNIV"],
    ),

    # 5. بيت لحم
    UniversityRules(
        id="bethlehem",
        name_ar="جامعة بيت لحم",
        name_en="Bethlehem University",
        institution_type="university",
        fingerprints=["جامعة بيت لحم", "Bethlehem University"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
            "حرة": "university",
        },
        prefixes=["COMP", "CS", "IS", "IT", "MATH", "STAT", "PHYS",
                   "ENGL", "ARAB", "ECON", "MGT", "ACC", "LAW",
                   "NUR", "COMM", "EDU", "SOC", "PSY",
                   "AI", "NET", "SEC", "WEB", "DB"],
    ),

    # 6. الخليل
    UniversityRules(
        id="hebron",
        name_ar="جامعة الخليل",
        name_en="Hebron University",
        institution_type="university",
        fingerprints=["جامعة الخليل", "Hebron University"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
            "حرة": "university",
        },
        prefixes=["CS", "IS", "IT", "SE", "MATH", "STAT", "PHYS",
                   "ENGL", "ARAB", "ECON", "MGT", "ACC", "LAW",
                   "NUR", "ENG", "CIV", "ELE", "MEC",
                   "AI", "NET", "SEC", "WEB", "DB"],
    ),

    # 7. الإسلامية - غزة
    UniversityRules(
        id="iug",
        name_ar="الجامعة الإسلامية - غزة",
        name_en="Islamic University of Gaza",
        institution_type="university",
        fingerprints=["الجامعة الإسلامية", "Islamic University of Gaza", "الإسلامية غزة"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "اختياري": "specialization",
            "كلية": "college",
            "جامعة": "university",
            "حرة": "university",
            "انتخابي": "university",
        },
        prefixes=["CSC", "CS", "IS", "IT", "SE", "NET", "MATH", "STAT",
                   "PHYS", "CHEM", "BIOL", "ENGL", "ARAB", "ENG",
                   "ECON", "MGT", "ACC", "FIN", "LAW", "EDU", "NUR",
                   "CIV", "ELE", "MEC", "ARC", "COMM",
                   "SHAR", "ISLM", "QUR", "FEQ",
                   "AI", "SEC", "WEB", "DB", "DATA", "ML"],
    ),

    # 8. الأزهر - غزة
    UniversityRules(
        id="alazhar_gaza",
        name_ar="جامعة الأزهر - غزة",
        name_en="Al-Azhar University - Gaza",
        institution_type="university",
        fingerprints=["جامعة الأزهر", "Al-Azhar University", "الأزهر غزة"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
            "حرة": "university",
        },
        prefixes=["CS", "IS", "IT", "SE", "MATH", "STAT", "PHYS",
                   "ENGL", "ARAB", "ECON", "MGT", "ACC", "LAW",
                   "NUR", "EDU", "COMM",
                   "SHAR", "ISLM", "QUR", "FEQ", "TAF",
                   "AI", "NET", "SEC", "WEB", "DB"],
    ),

    # 9. الأقصى
    UniversityRules(
        id="alaqsa",
        name_ar="جامعة الأقصى",
        name_en="Al-Aqsa University",
        institution_type="university",
        fingerprints=["جامعة الأقصى", "Al-Aqsa University"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
            "حرة": "university",
        },
        prefixes=["CS", "IS", "IT", "SE", "MATH", "STAT", "PHYS",
                   "ENGL", "ARAB", "ECON", "MGT", "ACC", "LAW",
                   "NUR", "EDU", "COMM", "SOC",
                   "AI", "NET", "SEC", "WEB", "DB"],
    ),

    # 10. القدس المفتوحة
    UniversityRules(
        id="qou",
        name_ar="جامعة القدس المفتوحة",
        name_en="Al-Quds Open University",
        institution_type="university",
        fingerprints=["القدس المفتوحة", "Open University", "QOU", "المفتوحة جامعة"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
            "حرة": "university",
            "انتخابي": "university",
        },
        prefixes=["CS", "IS", "IT", "SE", "MATH", "STAT", "ENGL", "ARAB",
                   "ECON", "MGT", "ACC", "EDU", "SOC", "PSY",
                   "AI", "NET", "SEC", "WEB", "DB", "GE", "GS"],
        ucas_pattern=r"$^",
    ),

    # 11. فلسطين التقنية - خضوري
    UniversityRules(
        id="ptuk",
        name_ar="جامعة فلسطين التقنية - خضوري",
        name_en="Palestine Technical University - Kadoorie",
        institution_type="university",
        fingerprints=["فلسطين التقنية", "خضوري", "Kadoorie", "Palestine Technical"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
            "حرة": "university",
        },
        prefixes=["COMP", "CS", "IT", "IS", "SE", "MATH", "STAT", "PHYS",
                   "ENGL", "ARAB", "ENG", "ECON", "MGT", "ACC",
                   "CIV", "ELE", "MEC", "ARC", "AGR",
                   "AI", "NET", "SEC", "WEB", "DB", "DATA"],
    ),

    # 12. فلسطين الأهلية
    UniversityRules(
        id="ahliya",
        name_ar="جامعة فلسطين الأهلية",
        name_en="Palestine Ahliya University",
        institution_type="university",
        fingerprints=["فلسطين الأهلية", "Palestine Ahliya"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
            "حرة": "university",
        },
        prefixes=["COMP", "CS", "IS", "IT", "SE", "MATH", "STAT",
                   "ENGL", "ARAB", "ECON", "MGT", "ACC",
                   "AI", "NET", "SEC", "WEB", "DB"],
    ),

    # 13. جامعة فلسطين
    UniversityRules(
        id="uop",
        name_ar="جامعة فلسطين",
        name_en="University of Palestine",
        institution_type="university",
        fingerprints=["جامعة فلسطين", "University of Palestine"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس", "بكلوريوس"],
        },
        course_type_map={
            "إجباري": "specialization",
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
            "حرة": "university",
        },
        prefixes=["COMP", "CS", "IS", "IT", "SE", "MATH", "STAT", "PHYS",
                   "ENGL", "ARAB", "ECON", "MGT", "ACC", "LAW",
                   "NUR", "COMM", "EDU", "CIV", "ELE", "MEC",
                   "AI", "NET", "SEC", "WEB", "DB", "DATA"],
    ),

    # 14. كلية المجتمع - العيزرية
    UniversityRules(
        id="cc_eizariya",
        name_ar="كلية المجتمع - العيزرية",
        name_en="Community College - Al-Eizariya",
        institution_type="community",
        fingerprints=["كلية المجتمع", "المجتمع العيزرية", "العيزرية", "Community College"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
        },
        course_type_map={
            "تخصص": "specialization",
            "إجباري": "specialization",
            "كلية": "college",
            "جامعة": "university",
        },
        prefixes=["COMP", "CS", "IS", "IT", "MATH", "STAT", "ENGL", "ARAB",
                   "ACC", "MGT", "NET", "SEC", "WEB", "DB", "UNIV"],
    ),

    # 15. الكلية الجامعية للعلوم والتكنولوجيا
    UniversityRules(
        id="ucst",
        name_ar="الكلية الجامعية للعلوم والتكنولوجيا",
        name_en="University College of Science and Technology",
        institution_type="college",
        fingerprints=["العلوم والتكنولوجيا", "Science and Technology"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس"],
        },
        course_type_map={
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
        },
        prefixes=["COMP", "CS", "IS", "IT", "MATH", "STAT", "ENGL", "ARAB",
                   "PHYS", "ECON", "MGT", "ACC",
                   "AI", "NET", "SEC", "WEB", "DB", "UNIV", "UNID"],
    ),

    # 16. الكلية الجامعية للتمريض
    UniversityRules(
        id="ucn",
        name_ar="الكلية الجامعية للتمريض",
        name_en="University College of Nursing",
        institution_type="college",
        fingerprints=["التمريض", "Nursing", "كلية التمريض"],
        degree_patterns={
            "diploma_intermediate": ["دبلوم متوسط"],
            "diploma_professional": ["دبلوم مهني"],
            "bachelor": ["بكالوريوس"],
        },
        course_type_map={
            "تخصص": "specialization",
            "كلية": "college",
            "جامعة": "university",
        },
        prefixes=["NUR", "NURS", "MATH", "STAT", "ENGL", "ARAB",
                   "BIO", "BIOL", "PHYS", "CHEM", "PSY", "SOC",
                   "MED", "PHA", "LAB", "NUT", "PHN", "UNIV", "UNID"],
    ),
]


# ═══════════════════════════════════════════════════════════════
#  Auto-Detection & Merging
# ═══════════════════════════════════════════════════════════════

def detect_university(text: str) -> UniversityRules:
    """
    Auto-detect institution from PDF text.
    Uses word-level matching to handle RTL-scrambled Arabic text.
    """
    # Stop words to ignore when doing word-level matching
    stop_words = {"the", "of", "and", "for", "in", "al", "في", "من", "على", "إلى"}

    def _score(fingerprints: List[str]) -> int:
        score = 0
        for fp in fingerprints:
            # Full match = instant win
            if fp in text:
                return 1000
            # Word-level: how many significant words match?
            words = [w for w in fp.split() if len(w) >= 3 and w.lower() not in stop_words]
            for w in words:
                if w in text:
                    score += len(w)  # Longer words = more specific = higher score
        return score

    scored = []
    for rules in REGISTRY:
        s = _score(rules.fingerprints)
        if s > 0:
            scored.append((s, rules))

    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        logger.debug(f"University detection scores: {[(s, r.id) for s, r in scored[:5]]}")
        return scored[0][1]

    return DEFAULT_RULES

def get_merged_rules(detected: UniversityRules) -> UniversityRules:
    merged = UniversityRules(
        id=detected.id or DEFAULT_RULES.id,
        name_ar=detected.name_ar or DEFAULT_RULES.name_ar,
        name_en=detected.name_en or DEFAULT_RULES.name_en,
        institution_type=detected.institution_type or DEFAULT_RULES.institution_type,
        fingerprints=detected.fingerprints or DEFAULT_RULES.fingerprints,
    )
    for field_name in ["degree_patterns", "course_type_map", "header_keywords"]:
        d = getattr(detected, field_name)
        dv = getattr(DEFAULT_RULES, field_name)
        setattr(merged, field_name, {**dv, **d} if d else dv)
    for field_name in ["prefixes", "skip_markers"]:
        d = getattr(detected, field_name)
        dv = getattr(DEFAULT_RULES, field_name)
        setattr(merged, field_name, d if d else dv)
    for field_name in [
        "total_hours_pattern", "spec_hours_pattern", "college_hours_pattern",
        "univ_hours_pattern", "ucas_pattern", "version_pattern", "date_pattern",
    ]:
        d = getattr(detected, field_name)
        dv = getattr(DEFAULT_RULES, field_name)
        setattr(merged, field_name, d if d else dv)
    return merged


def list_institutions() -> List[dict]:
    return [
        {
            "id": r.id,
            "name_ar": r.name_ar,
            "name_en": r.name_en,
            "type": r.institution_type,
            "prefixes_count": len(r.prefixes),
        }
        for r in REGISTRY
    ]