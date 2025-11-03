# --- Сборка Docker образа ---
build:
	docker build -t hungry_bot .

# --- Запуск контейнера Docker ---
run-docker:
	docker run -d -p 8443:80 hungry_bot -v $(pwd)/data:/app/data

# --- Локальный запуск без Docker ---
run:
	python -m app.main

# --- Установка зависимостей ---
install:
	pip install -r requirements.txt

# --- Тесты ---
test:
	python -m pytest -v

