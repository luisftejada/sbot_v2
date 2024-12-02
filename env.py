import os
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.config.database import Base
from dotenv import load_dotenv

# Cargar la URL de la base de datos desde la variable de entorno
import pdb; pdb.set_trace()
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_SBOTV2_DB_URL')

# Configuración de la conexión
config = context.config
config.set_section_option('alembic', 'sqlalchemy.url', DATABASE_URL)

# Otras configuraciones
target_metadata = Base.metadata

# Crear engine y conexión
engine = engine_from_config(
    config.get_section(config.config_ini_section),
    prefix='sqlalchemy.',
    poolclass=pool.NullPool
)
