PATH_ENV="./.venv"
PATH_PIP="$PATH_ENV/bin/pip"
rm -rf $PATH_ENV
python3 -m venv $PATH_ENV
$PATH_PIP install -r requirements.txt
