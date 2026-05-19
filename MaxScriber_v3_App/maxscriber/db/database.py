import json
import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Template(Base):
    __tablename__ = 'templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    format_name = Column(String, nullable=False, unique=True)
    user_name = Column(String, nullable=False)
    creation_date = Column(DateTime, default=datetime.datetime.utcnow)
    signature_hash = Column(String, nullable=False)
    config_json = Column(Text, nullable=False)

class DatabaseManager:
    def __init__(self, db_url: str = "sqlite:///maxscriber_registry.db"):
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def initialize_db(self):
        """Creates the database schema if it doesn't exist."""
        Base.metadata.create_all(bind=self.engine)

    def save_template(self, format_name: str, user_name: str, signature_hash: str, config_dict: dict) -> Template:
        """Saves a new template to the registry."""
        session = self.SessionLocal()
        try:
            config_json_str = json.dumps(config_dict)
            new_template = Template(
                format_name=format_name,
                user_name=user_name,
                signature_hash=signature_hash,
                config_json=config_json_str
            )
            session.add(new_template)
            session.commit()
            session.refresh(new_template)
            return new_template
        finally:
            session.close()

    def get_all_formats(self) -> List[Template]:
        """Retrieves all registered format templates."""
        session = self.SessionLocal()
        try:
            return session.query(Template).all()
        finally:
            session.close()

    def get_template_by_name(self, format_name: str) -> Optional[Template]:
        """Retrieves a specific template by its format name."""
        session = self.SessionLocal()
        try:
            return session.query(Template).filter(Template.format_name == format_name).first()
        finally:
            session.close()

# Singleton instance for easy import across modules
db_manager = DatabaseManager()
