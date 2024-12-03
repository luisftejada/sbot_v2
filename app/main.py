import os

from sqlalchemy import create_engine


def test_connection():
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "mydatabase")
    DB_USER = os.getenv("DB_USER", "myuser")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")

    DATABASE_URL = f"mariadb+mariadbconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"  # noqa E231

    # Create a database engine
    engine = create_engine(DATABASE_URL)

    # Test the connection
    try:
        with engine.connect() as connection:
            print(f"Successfully connected to the database!: {connection}")
    except Exception as e:
        print(f"Failed to connect to the database: {e}")


if __name__ == "__main__":
    test_connection()
