"""Language-agnostic structure, API, and data artifact detectors."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List

MAX_PATHS = 20

TOP_LEVEL_TAGS = {
    "src": "src-root",
    "app": "single-app",
    "apps": "multi-app",
    "packages": "monorepo-packages",
    "services": "services-folder",
    "modules": "modules-folder",
    "cmd": "go-cmd",
    "pkg": "go-pkg",
    "internal": "go-internal",
    "backend": "split-backend",
    "frontend": "split-frontend",
}

SERVICE_DIR_TAGS = {
    "routes": "routes",
    "routers": "routes",
    "controllers": "controllers",
    "api": "api",
    "apis": "api",
    "endpoints": "api",
    "handlers": "handlers",
    "services": "services",
    "models": "models",
    "schemas": "schemas",
    "migrations": "migrations",
    "db": "database",
    "database": "database",
    "domain": "domain",
    "domains": "domain",
}

API_FILE_PATTERNS = [
    re.compile(r"openapi", re.IGNORECASE),
    re.compile(r"swagger", re.IGNORECASE),
    re.compile(r"routes?.*\.(py|js|ts|tsx|go)$", re.IGNORECASE),
    re.compile(r"router.*\.(py|js|ts|tsx)$", re.IGNORECASE),
    re.compile(r"(postman|insomnia).*\.json$", re.IGNORECASE),
]

GRAPHQL_EXTENSIONS = {".graphql", ".gql", ".graphqls"}

DATA_FILE_PATTERNS = [
    re.compile(r"schema\.(sql|prisma)$", re.IGNORECASE),
    re.compile(r"schema\.(rb|py)$", re.IGNORECASE),
    re.compile(r"migrations?.*\.(sql|py|ts|js)$", re.IGNORECASE),
    re.compile(r"(ddl|tables?).*\.sql$", re.IGNORECASE),
]

ORM_FILES = {
    "schema.prisma": "prisma",
    "alembic.ini": "alembic",
    "env.py": "alembic-env",
    "ormconfig.json": "typeorm",
    "ormconfig.js": "typeorm",
    "knexfile.js": "knex",
    "liquibase.properties": "liquibase",
    "flyway.conf": "flyway",
}


def analyze_directory_layout(root: Path, directories: List[Path]) -> Dict[str, List[str]]:
    layout_tags: List[str] = []
    service_tags: Dict[str, int] = {}

    top_level = [d for d in directories if d.parent == root]
    for entry in top_level:
        tag = TOP_LEVEL_TAGS.get(entry.name.lower())
        if tag and tag not in layout_tags:
            layout_tags.append(tag)

    for directory in directories:
        key = SERVICE_DIR_TAGS.get(directory.name.lower())
        if key:
            service_tags[key] = service_tags.get(key, 0) + 1

    service_dirs = [d for d in directories if d.name.lower() in SERVICE_DIR_TAGS]

    return {
        "top_level_patterns": layout_tags,
        "service_markers": sorted(service_tags),
        "notable_directories": summarize_paths(service_dirs, root),
    }


def detect_api_artifacts(root: Path, files: Iterable[Path]) -> Dict[str, List[str]]:
    openapi_files: List[str] = []
    graphql_files: List[str] = []
    route_files: List[str] = []
    collections: List[str] = []

    for path in files:
        rel = path.relative_to(root)
        suffix = path.suffix.lower()
        if suffix in GRAPHQL_EXTENSIONS:
            graphql_files.append(str(rel))
            continue
        for pattern in API_FILE_PATTERNS:
            if pattern.search(str(rel)):
                if "openapi" in pattern.pattern or "swagger" in pattern.pattern:
                    openapi_files.append(str(rel))
                elif "postman" in pattern.pattern or "insomnia" in pattern.pattern:
                    collections.append(str(rel))
                else:
                    route_files.append(str(rel))
                break

    return {
        "openapi_files": truncate(openapi_files),
        "graphql_files": truncate(graphql_files),
        "route_files": truncate(route_files),
        "client_collections": truncate(collections),
    }


def detect_data_artifacts(root: Path, files: Iterable[Path], directories: Iterable[Path]) -> Dict[str, List[str]]:
    ddl_files: List[str] = []
    migration_dirs: List[str] = []
    orm_configs: List[str] = []
    seen_migration_dirs = set()

    for path in files:
        rel = str(path.relative_to(root))
        filename = path.name.lower()
        if filename in ORM_FILES:
            orm_configs.append(f"{rel} ({ORM_FILES[filename]})")
            continue
        for pattern in DATA_FILE_PATTERNS:
            if pattern.search(rel):
                ddl_files.append(rel)
                break

    for directory in directories:
        rel = str(directory.relative_to(root))
        name = directory.name.lower()
        if name in {"migrations", "migration", "db", "database", "schema"} or "alembic" in name:
            if rel not in seen_migration_dirs:
                seen_migration_dirs.add(rel)
                migration_dirs.append(rel)

    return {
        "ddl_files": truncate(ddl_files),
        "migration_dirs": truncate(migration_dirs),
        "orm_configs": truncate(orm_configs),
    }


def summarize_paths(paths: Iterable[Path], root: Path) -> List[str]:
    unique = []
    seen = set()
    for path in paths:
        try:
            value = str(path.relative_to(root))
        except ValueError:
            value = str(path)
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
        if len(unique) >= MAX_PATHS:
            break
    return unique


def truncate(items: List[str], limit: int = MAX_PATHS) -> List[str]:
    if len(items) <= limit:
        return items
    return items[: limit - 1] + ["..."]

