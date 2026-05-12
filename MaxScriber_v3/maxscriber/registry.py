import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path

class FormatRegistry:
    def __init__(self, db_path="maxscriber_registry.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database with the required schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                format_name TEXT NOT NULL UNIQUE,
                user_name TEXT NOT NULL,
                creation_date TEXT NOT NULL,
                signature_hash TEXT NOT NULL UNIQUE,
                config_json TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def _generate_hash(self, format_name: str) -> str:
        """Generates a stable signature hash for the template."""
        return hashlib.sha256(format_name.encode('utf-8')).hexdigest()

    def save_template(self, hospital_name: str, date_str: str, parameter_samples: str, user_name: str, config: dict):
        """
        Saves a template to the registry following the strict naming convention:
        <Hospital_Name>_<DDMMYYYY>_<parameter_samples>
        """
        format_name = f"{hospital_name}_{date_str}_{parameter_samples}"
        signature_hash = self._generate_hash(format_name)
        creation_date = datetime.now().isoformat()
        config_json = json.dumps(config)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO templates (format_name, user_name, creation_date, signature_hash, config_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (format_name, user_name, creation_date, signature_hash, config_json))
            conn.commit()
            print(f"[+] Successfully saved template: {format_name}")
            return True
        except sqlite3.IntegrityError:
            print(f"[-] Template or hash already exists for {format_name}")
            return False
        finally:
            conn.close()

    def get_template(self, format_name: str):
        """Retrieves a template configuration by format name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT config_json FROM templates WHERE format_name = ?", (format_name,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None

    def list_formats(self):
        """Lists all learned PDF structures."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, format_name, user_name, creation_date FROM templates ORDER BY creation_date DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {"id": r[0], "format_name": r[1], "user_name": r[2], "creation_date": r[3]}
            for r in rows
        ]

    def display_startup_box(self):
        """Prints a 'Saved Formats Box' upon initialization."""
        formats = self.list_formats()
        print("\n" + "="*50)
        print("          MaxScriber v3 - Format Registry          ")
        print("="*50)
        if not formats:
            print(" No saved formats found. Running in Discovery Mode.")
        else:
            print(f" Loaded {len(formats)} learned PDF structures:")
            for fmt in formats:
                print(f"  - [{fmt['id']}] {fmt['format_name']} (Mapped by: {fmt['user_name']} on {fmt['creation_date'][:10]})")
        print("="*50 + "\n")
