.PHONY: setup test clean build up down logs

setup:
	conda env create -f environment.yml
	conda activate trading-bot

test:
	conda run -n trading-bot pytest tests/ -v

clean:
	docker-compose down -v
	docker system prune -f

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

install:
	conda env update -f environment.yml

lint:
	conda run -n trading-bot black .
	conda run -n trading-bot flake8 .

dev:
	docker-compose up --build