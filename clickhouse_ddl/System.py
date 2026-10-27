import re

RE_FLAGS = re.IGNORECASE | re.MULTILINE

def QuoteName(name):
    if re.match(r"[\sА-Яа-я]{1,}", name, RE_FLAGS):
        return f"`{name}`"
    else:
        return name
