"""
Supported output formats for document generation.

Maps file extensions to categories and default filenames.
"""

from __future__ import annotations

# extension -> (category, default_basename, mime_type)
FORMAT_REGISTRY: dict[str, tuple[str, str, str]] = {
    # Business & productivity
    "pdf": ("business", "document", "application/pdf"),
    "docx": ("business", "document", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "pptx": ("business", "presentation", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    "xlsx": ("business", "spreadsheet", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "csv": ("business", "spreadsheet", "text/csv"),
    "md": ("business", "document", "text/markdown"),
    "rtf": ("business", "document", "application/rtf"),
    "txt": ("business", "document", "text/plain"),
    # Software development
    "py": ("code", "module", "text/x-python"),
    "js": ("code", "script", "text/javascript"),
    "ts": ("code", "module", "text/typescript"),
    "java": ("code", "Main", "text/x-java"),
    "c": ("code", "main", "text/x-c"),
    "cpp": ("code", "main", "text/x-c++"),
    "cs": ("code", "Program", "text/x-csharp"),
    "go": ("code", "main", "text/x-go"),
    "rs": ("code", "lib", "text/x-rust"),
    "php": ("code", "index", "application/x-php"),
    "rb": ("code", "app", "text/x-ruby"),
    "swift": ("code", "main", "text/x-swift"),
    "kt": ("code", "Main", "text/x-kotlin"),
    # Web
    "html": ("web", "index", "text/html"),
    "css": ("web", "styles", "text/css"),
    "scss": ("web", "styles", "text/x-scss"),
    "jsx": ("web", "Component", "text/jsx"),
    "tsx": ("web", "Component", "text/tsx"),
    "vue": ("web", "Component", "text/vue"),
    # Config
    "json": ("config", "config", "application/json"),
    "yaml": ("config", "config", "application/x-yaml"),
    "yml": ("config", "config", "application/x-yaml"),
    "toml": ("config", "config", "application/toml"),
    "xml": ("config", "config", "application/xml"),
    "env": ("config", "env", "text/plain"),
    # DevOps (extension-less names stored with pseudo-ext)
    "dockerfile": ("devops", "Dockerfile", "text/plain"),
    "tf": ("devops", "main", "text/plain"),
    # API / docs
    "graphql": ("api", "schema", "text/plain"),
    "sql": ("database", "schema", "application/sql"),
    # Archives
    "zip": ("project", "project", "application/zip"),
}

# Prompt keyword -> extension hints (checked before generic rules)
EXTENSION_KEYWORDS: dict[str, list[str]] = {
    "pdf": ["pdf", "portable document"],
    "docx": ["word document", "docx", "microsoft word"],
    "pptx": ["powerpoint", "pptx", "presentation slide"],
    "xlsx": ["excel", "xlsx", "spreadsheet"],
    "csv": ["csv file", "csv report", ".csv"],
    "md": ["markdown", "readme", "readme.md"],
    "py": ["python file", "python script", ".py"],
    "js": ["javascript file", ".js"],
    "ts": ["typescript file", ".ts"],
    "html": ["html file", "html page", ".html"],
    "json": ["json file", "json config"],
    "yaml": ["yaml file", "yaml config"],
    "yml": ["yml file"],
    "dockerfile": ["dockerfile"],
    "tf": ["terraform", ".tf"],
    "sql": ["sql script", "sql migration", "database migration"],
    "zip": ["project structure", "full project", "zip archive", "complete project"],
    "jsx": ["react component", ".jsx"],
    "tsx": ["react typescript", ".tsx"],
    "vue": ["vue component", ".vue"],
}

PROJECT_KEYWORDS = [
    "flask api", "fastapi backend", "react application", "next.js",
    "full-stack", "microservice", "rag application", "project structure",
    "scaffold", "boilerplate", "starter project",
]

IMAGE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "architecture_diagram": ["architecture diagram", "system diagram", "system architecture"],
    "flowchart": ["flowchart", "flow chart", "process flow"],
    "network_diagram": ["network diagram", "topology"],
    "database_diagram": ["database diagram", "erd", "entity relationship"],
    "ui_mockup": ["ui mockup", "dashboard mockup", "dashboard design", "wireframe"],
    "landing_page": ["landing page", "landing page design"],
    "infographic": ["infographic"],
    "logo": ["logo", "brand mark"],
    "concept_art": ["concept art", "illustration", "artwork"],
    "general": ["create an image", "generate an image", "draw", "picture of"],
}


def is_supported_extension(ext: str) -> bool:
    return ext.lower().lstrip(".") in FORMAT_REGISTRY


def mime_for_extension(ext: str) -> str:
    key = ext.lower().lstrip(".")
    entry = FORMAT_REGISTRY.get(key)
    return entry[2] if entry else "application/octet-stream"


def default_basename(ext: str) -> str:
    key = ext.lower().lstrip(".")
    entry = FORMAT_REGISTRY.get(key)
    return entry[1] if entry else "output"
