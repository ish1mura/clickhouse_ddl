SET CWD=%~dp0
SET ENV=.venv

rmdir /S /Q "%CWD%%ENV%"
"python.exe" -m venv "%CWD%%ENV%"

"%CWD%%ENV%/Scripts/pip" install clickhouse_driver

pause