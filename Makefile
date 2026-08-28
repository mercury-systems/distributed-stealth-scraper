.PHONY: build test demo clean install install-heavy lint

build:
	docker compose build

test:
	python3 -m pytest tests/ -v

demo:
	python3 -m stealth_scraper.demo_enhanced

clean:
	rm -rf __pycache__ .pytest_cache *.db src/*.egg-info dist build
	docker compose down --volumes --remove-orphans

install:
	pip install -r requirements.txt

install-heavy:
	pip install -r requirements.txt -r requirements-heavy.txt
	playwright install chromium

install-dev:
	pip install -r requirements.txt -r requirements-heavy.txt -r requirements-dev.txt
	playwright install chromium

lint:
	python3 -m py_compile src/stealth_scraper/*.py tests/*.py
