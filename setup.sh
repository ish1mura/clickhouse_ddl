PATH_CURRENT=$(dirname "$0")
PATH_PYTHON=$PATH_CURRENT/.venv/bin/python

rm -rf $PATH_CURRENT/build
rm -rf $PATH_CURRENT/dist
rm -rf $PATH_CURRENT/clickhouse_ddl.egg-info

$PATH_PYTHON $PATH_CURRENT/setup.py sdist bdist_wheel
$PATH_PYTHON -m twine upload $PATH_CURRENT/dist/* --verbose
