import json
import yaml
from pathlib import Path
from typing import List, Dict, Optional
import datetime

class SchemaManager:
    """Manages MaxScriber schemas in the global user directory."""

    def __init__(self):
        self.base_dir = Path.home() / '.maxscriber' / 'schemas'
        self.registry_file = self.base_dir / 'registry.json'
        self._ensure_setup()

    def _ensure_setup(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            self._write_registry({"schemas": []})

    def _read_registry(self) -> dict:
        with open(self.registry_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write_registry(self, data: dict):
        with open(self.registry_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get_all_schemas(self) -> List[Dict]:
        return self._read_registry().get("schemas", [])

    def save_schema(self, name: str, tests: List[str], metadata: dict, is_legacy: bool = False, description: str = ""):
        schema_file_name = f"{name}.yaml"
        schema_path = self.base_dir / schema_file_name

        schema_content = {
            "name": name,
            "version": "1.0",
            "metadata": metadata,
            "tests": tests
        }

        with open(schema_path, 'w', encoding='utf-8') as f:
            yaml.dump(schema_content, f, sort_keys=False)

        registry = self._read_registry()
        
        # Remove if exists to update
        registry["schemas"] = [s for s in registry["schemas"] if s["name"] != name]
        
        registry["schemas"].append({
            "name": name,
            "file": schema_file_name,
            "date_added": datetime.date.today().isoformat(),
            "is_legacy": is_legacy,
            "tests_count": len(tests),
            "description": description
        })
        
        self._write_registry(registry)

    def get_schema(self, name: str) -> Optional[dict]:
        registry = self._read_registry()
        for s in registry.get("schemas", []):
            if s["name"] == name:
                schema_path = self.base_dir / s["file"]
                if schema_path.exists():
                    with open(schema_path, 'r', encoding='utf-8') as f:
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
