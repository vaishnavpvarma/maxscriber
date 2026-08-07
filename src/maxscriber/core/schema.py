import datetime
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class SchemaManager:
    """Manages MaxScriber schemas in the global user directory and package defaults."""

    def __init__(self):
        self.base_dir = Path.home() / ".maxscriber" / "schemas"
        self.registry_file = self.base_dir / "registry.json"
        self.pkg_schemas_dir = Path(__file__).parent.parent / "schemas"
        self._ensure_setup()

    def _ensure_setup(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            self._write_registry({"schemas": []})

        # Sync built-in package schemas if not already present in registry
        registry = self._read_registry()
        registered_names = {s["name"] for s in registry.get("schemas", [])}

        if self.pkg_schemas_dir.exists():
            for schema_file in self.pkg_schemas_dir.glob("*.yaml"):
                name = schema_file.stem
                target_path = self.base_dir / schema_file.name
                if not target_path.exists():
                    shutil.copy(schema_file, target_path)

                if name not in registered_names:
                    try:
                        with open(schema_file, "r", encoding="utf-8") as f:
                            content = yaml.safe_load(f) or {}
                        tests = content.get("tests", [])
                        desc = content.get("description", "Built-in package schema")
                    except Exception:
                        tests = []
                        desc = "Built-in package schema"

                    registry["schemas"].append(
                        {
                            "name": name,
                            "file": schema_file.name,
                            "date_added": datetime.date.today().isoformat(),
                            "is_legacy": True,
                            "tests_count": len(tests),
                            "description": desc,
                        }
                    )
                    registered_names.add(name)
            self._write_registry(registry)

    def _read_registry(self) -> dict:
        with open(self.registry_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_registry(self, data: dict):
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_all_schemas(self) -> List[Dict]:
        return self._read_registry().get("schemas", [])

    def save_schema(
        self,
        name: str,
        tests: List[str],
        metadata: dict,
        is_legacy: bool = False,
        description: str = "",
    ):
        schema_file_name = f"{name}.yaml"
        schema_path = self.base_dir / schema_file_name

        schema_content = {"name": name, "version": "1.0", "metadata": metadata, "tests": tests}

        with open(schema_path, "w", encoding="utf-8") as f:
            yaml.dump(schema_content, f, sort_keys=False)

        registry = self._read_registry()

        # Remove if exists to update
        registry["schemas"] = [s for s in registry["schemas"] if s["name"] != name]

        registry["schemas"].append(
            {
                "name": name,
                "file": schema_file_name,
                "date_added": datetime.date.today().isoformat(),
                "is_legacy": is_legacy,
                "tests_count": len(tests),
                "description": description,
            }
        )

        self._write_registry(registry)

    def import_schema_file(self, file_path: Path) -> str:
        """Import a YAML schema file from any path into the registry."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Schema file {file_path} not found.")

        with open(file_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        if not isinstance(content, dict):
            raise ValueError("Invalid YAML schema structure.")

        name = content.get("name", file_path.stem)
        tests = content.get("tests", [])
        metadata = content.get("metadata", {})
        description = content.get("description", "Imported user schema")

        self.save_schema(name, tests, metadata, description=description)
        return name

    def get_schema(self, name_or_path: str) -> Optional[dict]:
        # 1. Check if name_or_path is a direct file path to a YAML file
        path_candidate = Path(name_or_path)
        if path_candidate.exists() and path_candidate.is_file():
            try:
                name = self.import_schema_file(path_candidate)
                schema_path = self.base_dir / f"{name}.yaml"
                with open(schema_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception:
                pass

        # 2. Check in user registry
        registry = self._read_registry()
        for s in registry.get("schemas", []):
            if s["name"] == name_or_path:
                schema_path = self.base_dir / s["file"]
                if schema_path.exists():
                    with open(schema_path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f)

        # 3. Fallback check in package schemas directory
        pkg_file = self.pkg_schemas_dir / f"{name_or_path}.yaml"
        if pkg_file.exists():
            with open(pkg_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return None

    def delete_schema(self, name: str) -> bool:
        registry = self._read_registry()
        initial_len = len(registry.get("schemas", []))

        target = next((s for s in registry.get("schemas", []) if s["name"] == name), None)
        if target:
            schema_path = self.base_dir / target["file"]
            if schema_path.exists():
                schema_path.unlink()

        registry["schemas"] = [s for s in registry.get("schemas", []) if s["name"] != name]
        self._write_registry(registry)

        return len(registry["schemas"]) < initial_len
