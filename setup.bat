rmdir /S /Q "./build"
rmdir /S /Q "./dist"
rmdir /S /Q "./clickhouse_ddl.egg-info"
"python.exe" "./setup.py" sdist bdist_wheel
rem "python.exe" -m twine upload --repository-url https://pypi.org/legacy/ dist/*
"python.exe" -m twine upload dist/*
pause