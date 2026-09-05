.PHONY: setup demo start test eval console clean

setup:
	python -m pip install -r requirements.txt
	cd console && npm install

test:
	python -m pytest -v --cov=backstop

eval:
	python -m backstop.eval.report

demo:
	python run.py

start:
	python run.py

console:
	cd console && npm run dev

clean:
	rm -rf data/ .pytest_cache/ .coverage htmlcov/ console/dist/
