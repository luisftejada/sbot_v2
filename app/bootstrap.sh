#! /bin/bash

export PYTHONPATH=.

# Verifica si la variable MODE está definida
if [ -z "$MODE" ]; then
  echo "Error: La variable de entorno MODE no está definida."
  echo "Define MODE antes de ejecutar el script (e.g., export MODE=bot)."
  exit 1
fi

# Ejecuta comandos según el valor de MODE
case "$MODE" in
  bot)
    echo "Modo bot"
    # Comandos específicos para el modo desarrollo
    poetry run python app/workers/bot.py
    ;;
  db-migrate)
    echo "Run alembic migrations"
    # Comandos específicos para el modo producción
    poetry run alembic upgrade head
    ;;
  test)
    echo "Test db connections"
    poetry run pytest tests
    ;;
  *)
    echo "Error: Valor no válido para MODE: $MODE"
    echo "Valores permitidos: bot, db-migrate"
    exit 1
    ;;
esac
