from app.config.database import Base, engine
from app.models.order import Order

if __name__ == "__main__":
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas con éxito.")