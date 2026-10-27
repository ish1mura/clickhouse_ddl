#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import os, shutil
from collections import namedtuple
from multiprocessing import Pool
from clickhouse_driver import Client

from clickhouse_ddl.Config import Config
from clickhouse_ddl.Function import Function
from clickhouse_ddl.Grant import Grant
from clickhouse_ddl.Role import Role
from clickhouse_ddl.Setting import Setting
from clickhouse_ddl.System import QuoteName
from clickhouse_ddl.Table import Table
from clickhouse_ddl.TableColumn import TableColumn
from clickhouse_ddl.View import View
from clickhouse_ddl.User import User

FileData = namedtuple("FileData", ["path", "data"])

class ClickHouseDDL(object):
    def __init__(self, path_config, path_result, connect_name):
        Config.Parse(path_config)

        self.Connect = Config.Connects.get(connect_name) or {}
        assert len(self.Connect.keys()) > 0, \
            f"No connect {connect_name} in config"

        self.Databases = []
        self.GetDatabases()
        print("Databases")

        self.Settings = []
        self.GetSettings()
        print("Settings")

        self.ServerSettings = []
        self.GetServerSettings()
        print("ServerSettings")

        self.Grants = {}
        self.GetGrants()
        print("Grants")

        self.RoleGrants = {}
        self.GetRoleGrants()
        print("RoleGrants")

        self.Roles = {}
        self.GetRoles()
        print("Roles")

        self.UserSettings = {}
        self.GetUserSettings()
        print("UserSettings")

        self.Users = {}
        self.GetUsers()
        print("Users")

        self.TablesColumns = {}
        self.GetTablesColumns()
        print("TablesColumns")

        self.Tables = {}
        self.GetTables()
        print("Tables")

        self.Functions = []
        self.GetFunctions()
        print("Functions")

        self.Views = {}
        self.GetViews()
        print("Views")

        self.Dictionaries = {}
        self.GetDictionaries()
        print("Dictionaries")

        self.Write(path_result)

    def GetData(self, query, params={}):
        with Client(
            host            = self.Connect.get("host"),
            port            = self.Connect.get("port"),
            database        = self.Connect.get("database"),
            user            = self.Connect.get("username"),
            password        = self.Connect.get("password"),
            connect_timeout = 86400,
            secure          = (self.Connect.get("secure") is True),
            ca_certs        = self.Connect.get("cacert")
        ) as ch:
            columns = None
            for row in ch.execute_iter(query, params, with_column_types=True, types_check=True):
                if columns is None:
                    columns = [column[0] for column in row]
                else:
                    yield dict(zip(columns, row))

    def GetDatabases(self):
        self.Databases.clear()

        for row in self.GetData("""
            SELECT d.name
            FROM system.databases d
            WHERE d.name not in ('INFORMATION_SCHEMA','information_schema','system')
        """):
            self.Databases.append(row.get("name"))

    def GetTablesColumns(self):
        self.TablesColumns.clear()

        for row in self.GetData("""
            SELECT *
            FROM system.columns
            WHERE database IN %(db)s
            ORDER BY database, table, position
        """,{
            "db": self.Databases,
        }):
            column = TableColumn(row)

            if column.TableFull not in self.TablesColumns.keys():
                self.TablesColumns[column.TableFull] = []
            self.TablesColumns[column.TableFull].append(column)

    def GetTables(self):
        self.Tables.clear()

        for tbl in self.GetData("""
            SELECT *
            FROM system.tables t
            WHERE
                t.engine NOT IN ('View','MaterializedView','Dictionary') AND
                t.database IN %(db)s
        """,{
            "db": self.Databases,
        }):
            table = Table(tbl)
            table.Columns = self.TablesColumns.get(table.NameFull) or {}
            table.Grants = self.Grants.get(table.NameFull) or {}

            if table.DB not in self.Tables.keys():
                self.Tables[table.DB] = {}
            self.Tables[table.DB][table.Name] = table

    def GetViews(self):
        self.Views.clear()

        for row in self.GetData("""
            SELECT *
            FROM system.tables t
            WHERE
                t.engine in ('View','MaterializedView') and
                t.database IN %(db)s
        """,{
            "db": self.Databases,
        }):
            view = View(row)
            view.Grants = self.Grants.get(view.NameFull) or {}

            for st in self.GetData(f"SHOW CREATE {view.NameFull}"):
                view.SetDDL(st.get("statement"), self.Functions)

            if view.DB not in self.Views.keys():
                self.Views[view.DB] = {}
            self.Views[view.DB][view.Name] = view

    def GetSettings(self):
        self.Settings.clear()
        for row in self.GetData("SELECT * FROM system.settings ORDER BY name"):
            self.Settings.append(Setting(row))

    def GetServerSettings(self):
        self.ServerSettings.clear()
        for row in self.GetData("SELECT * FROM system.server_settings ORDER BY name"):
            self.ServerSettings.append(Setting(row))

    def GetRoleGrants(self):
        self.RoleGrants = {}
        for row in self.GetData("""
            SELECT
                g.granted_role_name as child,
                coalesce(g.user_name, g.role_name) as parent
            FROM system.role_grants g
            ORDER BY 1,2
        """):
            role_parent = row.get("parent")
            role_child = row.get("child")
            ddl = f"GRANT {role_child} TO {role_parent};"

            if role_parent not in self.RoleGrants.keys():
                self.RoleGrants[role_parent] = []
            self.RoleGrants.get(role_parent).append(ddl)

            if role_child not in self.RoleGrants.keys():
                self.RoleGrants[role_child] = []
            self.RoleGrants.get(role_child).append(ddl)

    def GetGrants(self):
        self.Grants = {}
        for row in self.GetData("""
            select *
            from (
                SELECT
                    COALESCE(
                        nullif(trim(g.role_name), ''),
                        nullif(trim(g.user_name), '')
                    ) AS role_name,
                    g.access_type,
                    g.database,
                    g.table,
                    g.column,
                    g.grant_option
                FROM system.grants g
            ) q
            where q.role_name is not null
        """):
            grant = Grant(row)
            ddl = grant.GetDDL()

            if grant.RoleName not in self.Grants.keys():
                self.Grants[grant.RoleName] = []
            self.Grants[grant.RoleName].append(ddl)

            if len(grant.TableFull) > 0:
                if grant.TableFull not in self.Grants.keys():
                    self.Grants[grant.TableFull] = []
                self.Grants[grant.TableFull].append(ddl)

    def GetRoles(self):
        self.Roles.clear()

        for row in self.GetData("SELECT * FROM system.roles"):
            role = Role(row)
            role.Grants = self.Grants.get(role.Name) or []
            role.RoleGrants = self.RoleGrants.get(role.Name) or []
            self.Roles[role.Name] = role

    def GetUsers(self):
        self.Users.clear()

        for row in self.GetData("SELECT * FROM system.users"):
            user = User(row)
            user.Grants = self.Grants.get(user.Name) or []
            user.RoleGrants = self.RoleGrants.get(user.Name) or []
            user.UserSettings = self.UserSettings.get(user.Name) or {}
            self.Users[user.Name] = user

    def GetUserSettings(self):
        self.UserSettings = {}
        for row in self.GetData("""
            select *
            from system.settings_profile_elements e
            where
                e.user_name is not null and
                e.setting_name is not null and
                e.value is not null
            order by e.user_name, e.setting_name
        """):
            user_name = row.get("user_name")
            key = row.get("setting_name")
            val = row.get("value")
            if user_name not in self.UserSettings.keys():
                self.UserSettings[user_name] = {}
            self.UserSettings.get(user_name)[key] = val

    def GetFunctions(self):
        self.Functions.clear()

        for row in self.GetData("""
            select *
            from system.functions f
            where f.origin NOT IN ('System')
        """):
            self.Functions.append(Function(row))

    def GetDictionaries(self):
        self.Dictionaries = {}
        for row in self.GetData("""
            select *
            from system.tables f
            where f.engine in ('Dictionary')
        """):
            db = row.get("database")
            name = row.get("name")
            name_full = ".".join([db, QuoteName(name)])

            dfn = row.get("create_table_query") + ";"

            dfn = dfn.replace(" (`", f"({Config.NL}  `")
            dfn = dfn.replace(", `", f",{Config.NL}  `")
            dfn = dfn.replace(") PRIMARY", f"{Config.NL}){Config.NL}PRIMARY")
            dfn = dfn.replace(" SOURCE", f"{Config.NL}SOURCE")
            dfn = dfn.replace(" LIFETIME", f"{Config.NL}LIFETIME")
            dfn = dfn.replace(" LAYOUT", f"{Config.NL}LAYOUT")
            dfn = dfn.replace("PORT ", f"{Config.NL}  PORT ")
            dfn = dfn.replace(" HOST ", f"{Config.NL}  HOST ")
            dfn = dfn.replace(" USER ", f"{Config.NL}  USER ")
            dfn = dfn.replace(" PASSWORD ", f"{Config.NL}  PASSWORD ")
            dfn = dfn.replace(" DB ", f"{Config.NL}  DB ")
            dfn = dfn.replace(" TABLE ", f"{Config.NL}  TABLE ")
            dfn = dfn.replace("'))", f"'{Config.NL}))")

            ddl = f"-- Dictionary: {name}"
            ddl += Config.NL + Config.NL
            ddl += f"-- DROP DICTIONARY IF EXISTS {name};"
            ddl += Config.NL + Config.NL
            ddl += dfn;

            if name_full in self.Grants.keys():
                ddl += Config.NL + Config.NL
                for grant in self.Grants.get(name_full):
                    ddl += grant + Config.NL

            if db not in self.Dictionaries.keys():
                self.Dictionaries[db] = {}
            self.Dictionaries.get(db)[name] = ddl.strip()

    def Write(self, path):
        files = []

        # Recreate result path
        if os.path.exists(path):
            shutil.rmtree(path)
        os.mkdir(path)

        # Tables
        for db in self.Tables.keys():
            path_db = os.path.join(path, db)
            if not os.path.exists(path_db):
                os.mkdir(path_db)

            path_tables = os.path.join(path_db, "tables")
            if not os.path.exists(path_tables):
                os.mkdir(path_tables)

            for tbl in (self.Tables.get(db) or {}).values():
                files.append(FileData(
                    os.path.join(path_tables, f"{tbl.Name}.sql"),
                    tbl.GetDDL()
                ))

        # Views
        for db in self.Views.keys():
            path_db = os.path.join(path, db)
            if not os.path.exists(path_db):
                os.mkdir(path_db)

            path_views = os.path.join(path_db, "views")
            if not os.path.exists(path_views):
                os.mkdir(path_views)

            for view in (self.Views.get(db) or {}).values():
                files.append(FileData(
                    os.path.join(path_views, f"{view.Name}.sql"),
                    view.GetDDL()
                ))

        # Dictionaries
        for db in self.Dictionaries.keys():
            path_db = os.path.join(path, db)
            if not os.path.exists(path_db):
                os.mkdir(path_db)

            path_dicts = os.path.join(path_db, "dicts")
            if not os.path.exists(path_dicts):
                os.mkdir(path_dicts)

            for name, ddl in (self.Dictionaries.get(db) or {}).items():
                files.append(FileData(
                    os.path.join(path_dicts, f"{name}.sql"),
                    ddl
                ))

        # Roles
        path_roles = os.path.join(path, "roles")
        if not os.path.exists(path_roles):
            os.mkdir(path_roles)
        for role in self.Roles.values():
            files.append(FileData(
                os.path.join(path_roles, f"{role.Name}.sql"),
                role.GetDDL()
            ))

        # Users
        path_users = os.path.join(path, "users")
        if not os.path.exists(path_users):
            os.mkdir(path_users)
        for user in self.Users.values():
            files.append(FileData(
                os.path.join(path_users, f"{user.Name}.sql"),
                user.GetDDL()
            ))

        # Functions
        path_fnc = os.path.join(path, "functions")
        if not os.path.exists(path_fnc):
            os.mkdir(path_fnc)

        for fnc in self.Functions:
            files.append(FileData(
                os.path.join(path_fnc, f"{fnc.Name}.sql"),
                fnc.GetDDL()
            ))

        # Settings
        files.append(FileData(
            os.path.join(path, "settings.ini"),
            Config.NL.join([v.GetDDL() for v in sorted(self.Settings, key=lambda i: i.Name)])
        ))

        # Settings server
        files.append(FileData(
            os.path.join(path, "server_settings.ini"),
            Config.NL.join([v.GetDDL() for v in sorted(self.ServerSettings, key=lambda i: i.Name)])
        ))

        # Write to disc
        with Pool(processes=Config.Threads) as pool:
            pool.map(self.WriteFile, files)

    def WriteFile(self, prm):
        with open(prm.path, 'w', encoding="utf-8") as wf:
            wf.write(prm.data)
