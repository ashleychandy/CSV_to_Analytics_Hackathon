from src.db.database import Base, engine
from src.models.database_models import TransactionModel

def init_database():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_database() 