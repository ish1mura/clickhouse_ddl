PATH_CURRENT=$(dirname "$0")
PATH_ENV=$PATH_CURRENT/.venv

rm -rf $PATH_ENV
python3 -m venv $PATH_ENV
$PATH_ENV/bin/python -m pip install clickhouse_driver setuptools twine wheel
