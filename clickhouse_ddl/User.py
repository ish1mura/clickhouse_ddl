import json

from clickhouse_ddl.Config import Config

class User:
    def __init__(self, data):
        self.Name = data.get("name")

        self.AuthType = data.get("auth_type") or []

        self.AuthParams = data.get("auth_params") or []

        self.Grants = []

        self.RoleGrants = []

        self.UserSettings = {}

    def GetDDL(self):
        ddl = f"-- User: {self.Name}"
        ddl += Config.NL + Config.NL
        ddl += f"-- DROP USER IF EXISTS {self.Name};"
        ddl += Config.NL + Config.NL
        ddl += f"CREATE USER {self.Name}"
        ddl += Config.NL

        if len(self.AuthType) <= 0:
            ddl += "  NOT IDENTIFIED"
        else:
            for i, at in enumerate(self.AuthType):
                if i >= len(self.AuthParams):
                    continue
                ap = self.AuthParams[i].strip().lower()
                at = at.strip().lower()

                if at == "ldap" and ap not in ("", "{}"):
                    server = json.loads(ap).get("server")
                    ddl += f"  IDENTIFIED WITH {at} SERVER '{server}'"
                else:
                    ddl += f"  IDENTIFIED WITH {at}"

        ddl += ';' + Config.NL + Config.NL

        has_grant = False
        for grant in sorted(self.Grants):
            ddl += grant
            ddl += Config.NL
            has_grant = True

        if has_grant:
            ddl += Config.NL

        for grant in sorted(self.RoleGrants):
            ddl += grant
            ddl += Config.NL + Config.NL

        if len(self.UserSettings.keys()) > 0:
            ddl += f"ALTER USER {self.Name} SETTINGS"
            ddl += ",".join([f"{Config.NL}  {k} = {v}" for k,v in self.UserSettings.items()])
            ddl += ";" + Config.NL

        return ddl.strip() + Config.NL
