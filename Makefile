# --- Сборка Docker образа ---
build:
	docker build -t hungry_bot .

# --- Запуск контейнера Docker ---
run-docker:
	docker run -d -p 80:8443 hungry_bot

# --- Локальный запуск без Docker ---
run-local:
	python -m app.main

# --- Установка зависимостей ---
install:
	pip install -r requirements.txt
