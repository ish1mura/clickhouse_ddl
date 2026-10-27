from clickhouse_ddl.Config import Config

class Role:
    def __init__(self, data):
        self.Name = data.get("name")

        self.Grants = []

        self.RoleGrants = []

    def GetDDL(self):
        ddl = f"-- Role: {self.Name}"
        ddl += Config.NL + Config.NL
        ddl += f"-- DROP ROLE IF EXISTS {self.Name};"
        ddl += Config.NL + Config.NL
        ddl += f"CREATE ROLE {self.Name};"
        ddl += Config.NL + Config.NL

        has_grant = False
        for grant in sorted(self.Grants):
            ddl += grant
            ddl += Config.NL
            has_grant = True

        if has_grant:
            ddl += Config.NL

        for grant in sorted(self.RoleGrants):
            ddl += grant
            ddl += Config.NL

        return ddl.strip() + Config.NL
