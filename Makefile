.PHONY: setup demo test eval console clean

setup:
	python -m pip install -r requirements.txt
	cd console && npm install

test:
	python -m pytest -v --cov=backstop

eval:
	python -m backstop.eval.report

demo:
	python -m backstop.eval.report
	python -m uvicorn backstop.api:app --reload --port 8000

console:
	cd console && npm run dev

clean:
	rm -rf data/ .pytest_cache/ .coverage htmlcov/ console/dist/
