import json
import os
from datetime import datetime
from pathlib import Path

# File to store sequence counters persistently - store in the app/helpers directory
SEQUENCE_FILE = str(Path(__file__).parent / "matric_sequence.json")


def load_sequences():
    if os.path.exists(SEQUENCE_FILE):
        with open(SEQUENCE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_sequences(sequences):
    with open(SEQUENCE_FILE, "w") as f:
        json.dump(sequences, f, indent=2)


def get_next_sequence(school: str, year_suffix: str, branch: str = None, dept_code: str = None) -> str:
    """Generate next 4-digit sequence based on school + year + branch + department"""
    sequences = load_sequences()
    
    # Unique key for this combination
    key_parts = [school.upper()]
    if year_suffix:
        key_parts.append(year_suffix)
    if branch:
        key_parts.append(branch.upper())
    if dept_code:
        key_parts.append(dept_code.upper())
    
    key = "_".join(key_parts)
    
    next_num = sequences.get(key, 0) + 1
    sequences[key] = next_num
    save_sequences(sequences)
    
    return f"{next_num:04d}"


def preview_next_sequence(school: str, year_suffix: str, branch: str = None, dept_code: str = None) -> str:
    """Preview next 4-digit sequence WITHOUT incrementing it"""
    sequences = load_sequences()
    
    # Unique key for this combination
    key_parts = [school.upper()]
    if year_suffix:
        key_parts.append(year_suffix)
    if branch:
        key_parts.append(branch.upper())
    if dept_code:
        key_parts.append(dept_code.upper())
    
    key = "_".join(key_parts)
    
    next_num = sequences.get(key, 0) + 1
    return f"{next_num:04d}"


def generate_matric_number(
    school_initial: str,
    academic_year: str,           # e.g., "2025/2026" or "2026"
    department_code: str,         # e.g., "E", "B", "BM", "CS", "MED"
    branch: str = None,           # e.g., "Douala", "Yaounde", None
    extra_param: str = None       # Optional future use (e.g., "FT", "PT", "UG")
) -> str:
    
    # 1. School initial (must be 3 letters)
    school = school_initial.strip().upper()[:3]
    if len(school) != 3 or not school.isalpha():
        raise ValueError("School initial must be exactly 3 alphabetic characters.")
    
    # 2. Academic year → last two digits
    if "/" in academic_year:
        year_part = academic_year.split("/")[-1].strip()
    else:
        year_part = academic_year.strip()
    
    try:
        year_suffix = year_part[-2:]
        int(year_suffix)  # validate it's numeric
    except:
        raise ValueError("Invalid academic year format. Provide e.g., '2025/2026' or '2026'.")
    
    # 3. Branch initial (optional)
    branch_initial = branch.strip()[0].upper() if branch and branch.strip() else ""
    
    # 4. Department code (required now)
    dept = department_code.strip().upper()
    if not dept or not dept.isalnum():
        raise ValueError("Department code is required and must be alphabetic (e.g., E, B, BM, CS).")
    
    # 5. Sequence number (4 digits)
    sequence = get_next_sequence(school, year_suffix, branch_initial, dept)
    
    # 6. Build the matric number
    parts = [school, year_suffix]
    if branch_initial:
        parts.append(branch_initial)
    parts.append(dept)
    parts.append(sequence)
    
    matric = "".join(parts)
    
    # Optional extra parameter
    if extra_param:
        extra = extra_param.strip().upper()
        matric += f"/{extra}"
    
    return matric


# ========================
# Example Usage
# ========================

if __name__ == "__main__":
    print("=== Student Matriculation Number Generator ===\n")
    
    school = "UDS"
    year = "2025/2026"
    
    # Engineering in Douala
    m1 = generate_matric_number(school, year, department_code="E", branch="Douala")
    print("Engineering (Douala):", m1)
    
    m2 = generate_matric_number(school, year, department_code="E", branch="Douala")
    print("Next Engineering   :", m2)
    
    # Business (no branch)
    m3 = generate_matric_number(school, year, department_code="B", branch=None)
    print("Business (No branch):", m3)
    
    # Biomedical in Yaounde
    m4 = generate_matric_number(school, year, department_code="BM", branch="Yaounde")
    print("Biomedical (Yaounde):", m4)
    
    # With extra parameter (optional)
    m5 = generate_matric_number(school, "2026", "CS", "Douala", extra_param="FT")
    print("Computer Science    :", m5)