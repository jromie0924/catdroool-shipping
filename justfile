test:
  pipenv run pytest -v

install:
  pipenv sync

build:
  just --justfile {{justfile()}} install
  just --justfile {{justfile()}} test
