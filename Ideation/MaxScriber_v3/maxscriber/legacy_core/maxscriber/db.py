import json
import sqlite3
from pathlib import Path


class MaxScriberDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Patients Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    max_id TEXT PRIMARY KEY,
                    sin_no TEXT,
                    gender TEXT,
                    age TEXT
                )
            """)

            # Encounters Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS encounters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    max_id TEXT,
                    file_name TEXT,
                    collection_date TEXT,
                    FOREIGN KEY(max_id) REFERENCES patients(max_id)
                )
            """)

            # Lab Results Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lab_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    encounter_id INTEGER,
                    test_name TEXT,
                    value TEXT,
                    FOREIGN KEY(encounter_id) REFERENCES encounters(id)
                )
            """)

            # Metadata Table (for pipeline state like failed_files, qc_duplicates)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            conn.commit()

    def save_pipeline_state(self, key: str, value):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pipeline_state (key, value)
                VALUES (?, ?)
            """,
                (key, json.dumps(value)),
            )

    def load_pipeline_state(self, key: str, default=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM pipeline_state WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return default if default is not None else {}

    def insert_extraction(self, file_name: str, meta: dict, test_data: dict):
        self.insert_extractions_bulk([(file_name, meta, test_data)])

    def insert_extractions_bulk(self, extractions: list):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Start transaction for bulk insert
            for file_name, meta, test_data in extractions:
                max_id = meta.get("MAX_id") or f"UNKNOWN_{file_name}"
                sin_no = meta.get("SIN_No", "nil")
                gender = meta.get("Gender", "nil")
                age = meta.get("Age", "nil")

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO patients (max_id, sin_no, gender, age)
                    VALUES (?, ?, ?, ?)
                """,
                    (max_id, sin_no, gender, age),
                )

                if age and age != "nil":
                    cursor.execute(
                        'UPDATE patients SET age = ? WHERE max_id = ? AND (age IS NULL OR age = "nil")',
                        (age, max_id),
                    )

                for test_name, date_values in test_data.items():
                    for collection_date, value in date_values.items():
                        cursor.execute(
                            """
                            SELECT id FROM encounters WHERE file_name = ? AND collection_date = ?
                        """,
                            (file_name, collection_date),
                        )
                        row = cursor.fetchone()
                        if row:
                            encounter_id = row[0]
                        else:
                            cursor.execute(
                                """
                                INSERT INTO encounters (max_id, file_name, collection_date)
                                VALUES (?, ?, ?)
                            """,
                                (max_id, file_name, collection_date),
                            )
                            encounter_id = cursor.lastrowid

                        cursor.execute(
                            """
                            INSERT INTO lab_results (encounter_id, test_name, value)
                            VALUES (?, ?, ?)
                        """,
                            (encounter_id, test_name, str(value)),
                        )

            conn.commit()

    def get_all_extractions(self):
        """Reconstructs the `all_extractions` list format."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.file_name, p.max_id, p.sin_no, p.gender, p.age, e.id, e.collection_date
                FROM encounters e
                JOIN patients p ON e.max_id = p.max_id
            """)
            encounters = cursor.fetchall()

            file_groups = {}
            for row in encounters:
                fname, mid, sin, gender, age, enc_id, cdate = row
                if fname not in file_groups:
                    file_groups[fname] = {
                        "meta": {"MAX_id": mid, "SIN_No": sin, "Gender": gender, "Age": age},
                        "enc_ids": {},
                    }
                file_groups[fname]["enc_ids"][enc_id] = cdate

            all_extractions = []
            for fname, grp in file_groups.items():
                test_data = {}
                for enc_id, cdate in grp["enc_ids"].items():
                    cursor.execute(
                        "SELECT test_name, value FROM lab_results WHERE encounter_id = ?", (enc_id,)
                    )
                    for test_name, val in cursor.fetchall():
                        if test_name not in test_data:
                            test_data[test_name] = {}
                        test_data[test_name][cdate] = val

                all_extractions.append((fname, grp["meta"], test_data))

            return all_extractions
