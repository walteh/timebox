APP_NAME := Timebox

.PHONY: install build run clean

install:
	python -m pip install .
	python -m pip install py2app

build:
	python setup.py py2app -A

run:
	python main.py

clean:
	rm -rf build dist *.egg-info

release:
	python setup.py py2app
	cd dist && zip -r "$(APP_NAME).app.zip" "$(APP_NAME).app"
