launch:
	@echo Checking port 8000...
	-@cmd /C "for /f \"tokens=5\" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a"
	@echo Starting FastAPI...
	@uvicorn server:app --reload

run:
	@echo Freeing port 8000 if occupied...
	@-for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%p >nul 2>&1
	@echo "Launching application..."
	@.\env\Scripts\activate && uvicorn server:app --reload --port 8000 --host 0.0.0.0

up:
	@echo "Freeing port 8000 if occupied..."
	@pid=$$(lsof -ti:8000); if [ ! -z "$$pid" ]; then kill -9 $$pid; fi
	@echo "Launching application..."
	source env/Scripts/activate && uvicorn server:app --reload --port 8000 --host 0.0.0.0

test:
	pytest -v --tb=short --disable-warnings app/tests/test_tenants.py 