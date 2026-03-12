#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


CAREER_ROOT = Path(__file__).resolve().parents[4] / "career"
CV_SOURCE_PATH = CAREER_ROOT / "profile" / "cv_plain.txt"
CV_SOURCE_EXAMPLE_PATH = CAREER_ROOT / "profile" / "cv_plain.example.txt"
LATEX_PATH = CAREER_ROOT / "profile" / "render" / "main.tex"

SECTION_HEADERS = {
    "HEADLINE",
    "SUMMARY",
    "CAREER FOCUS",
    "SKILLS",
    "EXPERIENCE",
    "EDUCATION",
    "PROJECTS",
    "EVIDENCE BANK",
}

CONTACT_PREFIXES = {
    "Base": "base",
    "Email": "email",
    "Mobile": "mobile",
    "LinkedIn": "linkedin",
    "GitHub": "github",
    "Kaggle": "kaggle",
    "Toptal": "toptal",
}

TEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

COMPANY_RE = re.compile(r"^(?P<company>.+) \((?P<industry>.+)\) — (?P<location>.+)$")
ROLE_RE = re.compile(r"^(?P<title>.+) — (?P<start>.+) to (?P<end>.+)$")
EDUCATION_RE = re.compile(r"^(?P<degree>.+) — (?P<institution>.+) \((?P<start>.+) to (?P<end>.+)\)$")
PROJECT_RE = re.compile(r"^(?P<name>.+) — (?P<label>.+)$")


def tex_escape(value: object) -> str:
    text = str(value)
    for source, target in TEX_ESCAPES.items():
        text = text.replace(source, target)
    return text


def load_lines(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"missing {path}. Seed it from {CV_SOURCE_EXAMPLE_PATH} before rendering artifacts."
        )
    return path.read_text(encoding="utf-8").splitlines()


def split_sections(lines: list[str]) -> tuple[str, dict[str, str], dict[str, list[str]]]:
    nonempty = [line for line in lines if line.strip()]
    if not nonempty:
        raise ValueError("cv_plain.txt is empty")

    name = nonempty[0].strip()
    contacts: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current_section: str | None = None

    for line in lines[1:]:
        stripped = line.strip()
        if stripped in SECTION_HEADERS:
            current_section = stripped
            sections[current_section] = []
            continue

        if current_section is None:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                if key in CONTACT_PREFIXES:
                    contacts[CONTACT_PREFIXES[key]] = value.strip()
            continue

        sections[current_section].append(line.rstrip())

    return name, contacts, sections


def clean_lines(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line.strip()]


def parse_headline(lines: list[str]) -> str:
    cleaned = clean_lines(lines)
    if not cleaned:
        raise ValueError("HEADLINE section is missing content")
    return cleaned[0]


def parse_summary(lines: list[str]) -> list[str]:
    return [line[2:].strip() for line in clean_lines(lines) if line.startswith("- ")]


def parse_skills(lines: list[str]) -> dict[str, list[str]]:
    skills: dict[str, list[str]] = {}
    for line in clean_lines(lines):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        skills[key.strip()] = [item.strip() for item in value.split(",") if item.strip()]
    return skills


def parse_experience(lines: list[str]) -> list[dict]:
    companies: list[dict] = []
    current_company: dict | None = None
    current_role: dict | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        company_match = COMPANY_RE.match(line)
        if company_match:
            current_company = {
                "company": company_match.group("company").strip(),
                "industry": company_match.group("industry").strip(),
                "location": company_match.group("location").strip(),
                "roles": [],
            }
            companies.append(current_company)
            current_role = None
            continue

        role_match = ROLE_RE.match(line)
        if role_match:
            if current_company is None:
                raise ValueError(f"role found before company in EXPERIENCE: {line}")
            current_role = {
                "title": role_match.group("title").strip(),
                "start": role_match.group("start").strip(),
                "end": role_match.group("end").strip(),
                "tags": [],
                "bullets": [],
            }
            current_company["roles"].append(current_role)
            continue

        if line.startswith("Tags: "):
            if current_role is None:
                raise ValueError(f"tags found before role in EXPERIENCE: {line}")
            current_role["tags"] = [item.strip() for item in line.removeprefix("Tags: ").split(",") if item.strip()]
            continue

        if line.startswith("- "):
            if current_role is None:
                raise ValueError(f"bullet found before role in EXPERIENCE: {line}")
            current_role["bullets"].append(line[2:].strip())
            continue

    return companies


def parse_education(lines: list[str]) -> list[dict]:
    entries: list[dict] = []
    current_entry: dict | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        entry_match = EDUCATION_RE.match(line)
        if entry_match:
            current_entry = {
                "degree": entry_match.group("degree").strip(),
                "institution": entry_match.group("institution").strip(),
                "start": entry_match.group("start").strip(),
                "end": entry_match.group("end").strip(),
                "location": "",
                "details": [],
            }
            entries.append(current_entry)
            continue

        if not line.startswith("- ") or current_entry is None:
            continue

        payload = line[2:].strip()
        if payload.startswith("Details: "):
            details = payload.removeprefix("Details: ")
            current_entry["details"] = [item.strip() for item in details.split(",") if item.strip()]
        else:
            current_entry["location"] = payload

    return entries


def parse_projects(lines: list[str]) -> list[dict]:
    projects: list[dict] = []
    current_project: dict | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        project_match = PROJECT_RE.match(line)
        if project_match and not line.startswith("- "):
            current_project = {
                "name": project_match.group("name").strip(),
                "label": project_match.group("label").strip(),
                "bullets": [],
                "links": [],
            }
            projects.append(current_project)
            continue

        if not line.startswith("- ") or current_project is None:
            continue

        payload = line[2:].strip()
        if payload.startswith("Link: "):
            current_project["links"].append(payload.removeprefix("Link: ").strip())
        else:
            current_project["bullets"].append(payload)

    return projects


def parse_cv_source(path: Path) -> dict:
    name, contacts, sections = split_sections(load_lines(path))

    return {
        "name": name,
        "contacts": contacts,
        "headline": parse_headline(sections["HEADLINE"]) if "HEADLINE" in sections else "",
        "summary": parse_summary(sections.get("SUMMARY", [])),
        "career_focus": clean_lines(sections.get("CAREER FOCUS", [])),
        "skills": parse_skills(sections.get("SKILLS", [])),
        "experience": parse_experience(sections.get("EXPERIENCE", [])),
        "education": parse_education(sections.get("EDUCATION", [])),
        "projects": parse_projects(sections.get("PROJECTS", [])),
    }


def render_latex(profile: dict) -> str:
    contacts = profile["contacts"]
    lines: list[str] = []
    lines.append("% Generated from career/profile/cv_plain.txt by .agents/skills/cv-optimize/scripts/render_artifacts.py")
    lines.append(r"\documentclass[10pt,a4paper]{article}")
    lines.append(r"\usepackage[T1]{fontenc}")
    lines.append(r"\usepackage[utf8]{inputenc}")
    lines.append(r"\usepackage[margin=1.4cm]{geometry}")
    lines.append(r"\usepackage[hidelinks]{hyperref}")
    lines.append(r"\usepackage{enumitem}")
    lines.append(r"\usepackage{titlesec}")
    lines.append(r"\setlist[itemize]{leftmargin=1.2em,itemsep=2pt,topsep=2pt}")
    lines.append(r"\pagenumbering{gobble}")
    lines.append(r"\titleformat{\section}{\large\bfseries}{}{0em}{}[\titlerule]")
    lines.append(r"\begin{document}")
    lines.append(r"\begin{center}")
    lines.append(r"{\LARGE \textbf{" + tex_escape(profile["name"]) + r"}}\\[4pt]")
    if contacts.get("base"):
        lines.append(tex_escape(contacts["base"]) + r"\\")

    primary_contact_bits: list[str] = []
    if contacts.get("email"):
        primary_contact_bits.append(
            r"\href{mailto:" + contacts["email"] + "}{" + tex_escape(contacts["email"]) + r"}"
        )
    if contacts.get("mobile"):
        primary_contact_bits.append(tex_escape(contacts["mobile"]))
    if primary_contact_bits:
        lines.append(r" \quad ".join(primary_contact_bits) + r"\\")

    social_bits: list[str] = []
    if contacts.get("linkedin"):
        social_bits.append(r"\href{" + contacts["linkedin"] + r"}{LinkedIn}")
    if contacts.get("github"):
        social_bits.append(r"\href{" + contacts["github"] + r"}{GitHub}")
    if contacts.get("kaggle"):
        social_bits.append(r"\href{" + contacts["kaggle"] + r"}{Kaggle}")
    if contacts.get("toptal"):
        social_bits.append(r"\href{" + contacts["toptal"] + r"}{Toptal}")
    if social_bits:
        lines.append(r" \quad ".join(social_bits))
    lines.append(r"\end{center}")

    if profile["headline"]:
        lines.append(r"\section*{Headline}")
        lines.append(tex_escape(profile["headline"]))

    if profile["summary"]:
        lines.append(r"\section*{Summary}")
        lines.append(r"\begin{itemize}")
        for item in profile["summary"]:
            lines.append(r"\item " + tex_escape(item))
        lines.append(r"\end{itemize}")

    if profile["career_focus"]:
        lines.append(r"\section*{Career Focus}")
        lines.append(r"\begin{itemize}")
        for item in profile["career_focus"]:
            lines.append(r"\item " + tex_escape(item))
        lines.append(r"\end{itemize}")

    if profile["skills"]:
        lines.append(r"\section*{Skills}")
        for group, values in profile["skills"].items():
            lines.append(r"\textbf{" + tex_escape(group) + "}: " + tex_escape(", ".join(values)) + r"\\")

    if profile["experience"]:
        lines.append(r"\section*{Experience}")
        for company in profile["experience"]:
            lines.append(
                r"\subsection*{"
                + tex_escape(company["company"])
                + r" \hfill "
                + tex_escape(company["location"])
                + "}"
            )
            lines.append(r"\textit{" + tex_escape(company["industry"]) + r"}\\")
            for role in company["roles"]:
                lines.append(
                    r"\textbf{"
                    + tex_escape(role["title"])
                    + r"} \hfill "
                    + tex_escape(role["start"])
                    + " -- "
                    + tex_escape(role["end"])
                    + r"\\"
                )
                if role["tags"]:
                    lines.append(r"\textit{" + tex_escape(", ".join(role["tags"])) + "}")
                if role["bullets"]:
                    lines.append(r"\begin{itemize}")
                    for bullet in role["bullets"]:
                        lines.append(r"\item " + tex_escape(bullet))
                    lines.append(r"\end{itemize}")

    if profile["education"]:
        lines.append(r"\section*{Education}")
        for entry in profile["education"]:
            lines.append(
                r"\textbf{"
                + tex_escape(entry["degree"])
                + r"} \hfill "
                + tex_escape(entry["start"])
                + " -- "
                + tex_escape(entry["end"])
                + r"\\"
            )
            location_text = tex_escape(entry["location"]) if entry["location"] else ""
            institution_line = tex_escape(entry["institution"])
            if location_text:
                institution_line += ", " + location_text
            lines.append(institution_line + r"\\")
            if entry["details"]:
                lines.append(r"\textit{" + tex_escape(", ".join(entry["details"])) + r"}\\")

    if profile["projects"]:
        lines.append(r"\section*{Projects}")
        for project in profile["projects"]:
            lines.append(r"\textbf{" + tex_escape(project["name"]) + "} (" + tex_escape(project["label"]) + r")\\")
            lines.append(r"\begin{itemize}")
            for bullet in project["bullets"]:
                lines.append(r"\item " + tex_escape(bullet))
            for link in project["links"]:
                lines.append(r"\item \href{" + link + "}{" + tex_escape(link) + "}")
            lines.append(r"\end{itemize}")

    lines.append(r"\end{document}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render LaTeX resume artifacts from the canonical cv_plain.txt.")
    parser.add_argument("--source", default=str(CV_SOURCE_PATH), help="Path to the canonical cv_plain.txt file.")
    parser.add_argument("--output", default=str(LATEX_PATH), help="Path to the generated LaTeX file.")
    return parser.parse_args()


def main() -> None:
    try:
        args = parse_args()
        source_path = Path(args.source).resolve()
        output_path = Path(args.output).resolve()
        profile = parse_cv_source(source_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_latex(profile), encoding="utf-8")
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
