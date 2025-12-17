.PHONY: setup data

setup:
	pip install -r requirements.txt

data:
	mkdir -p data/raw
	kaggle datasets download -d jeanmidev/smart-meters-in-london -p data/raw
	unzip -o data/raw/*.zip -d data/raw
