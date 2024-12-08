.PHONY: build run clean remove run-ssh help

# Nombre de la imagen y etiqueta
IMAGE_NAME=bot2
TAG=latest
DOCKERPATH=docker/Dockerfile
BUILDCONTEXT=docker
NETWORK=my_app_network

# Default goal (el comando que se ejecuta si solo llamas a `make`)
.DEFAULT_GOAL := build

# Regla para construir la imagen
build:
	docker build \
		-f $(DOCKERPATH) -t $(IMAGE_NAME):$(TAG) \
		.

# Regla para ejecutar el contenedor
run:
	docker run -e MODE=bot \
	--network $(NETWORK) \
	--env-file .env \
	--rm -it $(IMAGE_NAME):$(TAG)

# Regla para limpiar imágenes dangling (sin etiquetas)
clean:
	docker image prune -f

# Regla para eliminar la imagen creada
remove:
	docker rmi $(IMAGE_NAME):$(TAG)

run-ssh:
	docker run -e MODE=bot \
	--network $(NETWORK) \
	--rm \
	--env-file .env \
	-it $(IMAGE_NAME):$(TAG) /bin/bash

run-migrations:
	docker run -e MODE=db-migrate \
	--network $(NETWORK) \
	--env-file .env \
	--rm -it $(IMAGE_NAME):$(TAG)

run-tests:
	docker run -e MODE=test \
	--network $(NETWORK) \
	--env-file .env \
	--rm -it $(IMAGE_NAME):$(TAG)

setup-mariadb:
	sudo systemctl stop mysql && \
	docker run -d \
	   --name mariadb \
	   --network $(NETWORK) \
       --env-file .env \
	   -v ~/datos/maridadb-vol:/var/lib/mysql \
	   -v $(pwd)/my.cnf:/etc/mysql/conf.d/my.cnf \
	   -p 3306:3306 \
	   mariadb:latest

clean-docker:
	docker stop $$(docker ps -a -q) && docker rm $$(docker ps -a -q) && docker rmi $$(docker images -q)

lint:
	poetry run pre-commit run --all-files

# Ayuda para mostrar los comandos disponibles
help:
	@echo "Makefile Docker Helper"
	@echo "Targets:"
	@echo "  build   - Construye la imagen Docker"
	@echo "  run     - Ejecuta un contenedor con la imagen"
	@echo "  clean   - Limpia imágenes dangling (sin etiquetas)"
	@echo "  remove  - Elimina la imagen Docker creada"
