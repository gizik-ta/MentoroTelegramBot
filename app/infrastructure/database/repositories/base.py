from infrastructure.database.connection import DatabaseConnection


class BaseRepository:
    def __init__(self, db: DatabaseConnection):
        self.db = db
