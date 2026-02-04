.PHONY: test install clean

install:
	pip install -r requirements.txt

test:
	python -m pytest test_main.py -v

run:
	python main.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete