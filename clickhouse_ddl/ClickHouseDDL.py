#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import os, re, json
from multiprocessing import Pool
from clickhouse_driver import Client
from clickhouse_ddl.Config import Config
from clickhouse_ddl.Function import Function

RE_FLAGS = re.MULTILINE | re.IGNORECASE

class ClickHouseDDL(object):
    def __init__(self, path):
        self.Databases = []
        self.GetDatabases()
        print("Databases")

        self.Columns = {}
        self.GetColumns()
        print("Columns")

        self.Settings = {}
        self.GetSettings()
        print("Settings")

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

        self.Tables = {}
        self.GetTables()
        print("Tables")

        self.Functions = {}
        self.GetFunctions()
        print("Functions")

        self.Views = {}
        self.GetViews()
        print("Views")

        self.Dictionaries = {}
        self.GetDictionaries()
        print("Dictionaries")

        self.Write(path)

    def GetData(self, query, params={}):
        with Client(
            host            = Config.Connect.get('host'),
            port            = Config.Connect.get('port'),
            database        = Config.Connect.get('database'),
            user            = Config.Connect.get('username'),
            password        = Config.Connect.get('password'),
            connect_timeout = 86400,
            secure          = (Config.Connect.get('secure') is True),
            ca_certs        = Config.Connect.get('cacert')
        ) as ch:
            columns = None
            for row in ch.execute_iter(query, params, with_column_types=True, types_check=True):
                if columns is None:
                    columns = [column[0] for column in row]
                else:
                    yield dict(zip(columns, row))

    def QuoteName(self, name):
        if re.match(r"[\sА-Яа-я]{1,}", name, re.IGNORECASE | re.MULTILINE):
            return f"`{name}`"
        else:
            return name

    def GetDatabases(self):
        self.Databases = []
        for row in self.GetData("""
            SELECT *
            FROM system.databases d
            WHERE d.name not in ('INFORMATION_SCHEMA','information_schema','system')
        """):
            self.Databases.append(row.get("name"))

    def GetColumns(self):
        self.Columns = {}
        for row in self.GetData("""
            SELECT *
            FROM system.columns
            WHERE database not in ('INFORMATION_SCHEMA','information_schema','system')
            ORDER BY database, table, position
        """):
            table_full = ".".join([row.get("database"), row.get("table")])
            if table_full not in self.Columns.keys():
                self.Columns[table_full] = []

            row["name"] = self.QuoteName(row.get("name"))

            default = ""
            if (row.get("default_kind") or "") == "DEFAULT":
                default = " {0} {1}".format(row.get("default_kind"), row.get("default_expression"))

            self.Columns.get(table_full).append("  {0} {1}{2}{3}".format(
                row.get("name"),
                row.get("type"),
                default,
                "" if len(row.get("comment") or "") <= 0 else " COMMENT '{0}'".format(row.get("comment"))
            ))

    def GetTables(self):
        self.Tables = {}
        for tbl in self.GetData("""
            SELECT *
            FROM system.tables t
            WHERE
                t.engine not in ('View','MaterializedView','Dictionary') and
                t.database not in ('INFORMATION_SCHEMA','information_schema','system')
        """):
            tbl_db = tbl.get("database")
            if tbl_db not in self.Databases:
                continue

            tbl_name = tbl.get("name")
            tbl_sql  = ".".join([tbl_db, self.QuoteName(tbl_name)])
            tbl_full = ".".join([tbl_db, tbl_name])

            columns = ",{0}".format(Config.NL).join(self.Columns.get(tbl_full))

            engine = tbl.get("engine_full")
            engine = engine.replace(" PARTITION BY", f"{Config.NL}PARTITION BY")
            engine = engine.replace(" PRIMARY KEY", f"{Config.NL}PRIMARY KEY")
            engine = engine.replace(" ORDER BY", f"{Config.NL}ORDER BY")
            engine = engine.replace(" SETTINGS", f"{Config.NL}SETTINGS")
            engine = f"ENGINE = {engine}"

            ddl = f"-- Table: {tbl_sql}"
            ddl += Config.NL + Config.NL
            ddl += f"-- DROP TABLE IF EXISTS {tbl_sql};"
            ddl += Config.NL + Config.NL
            ddl += f"CREATE TABLE {tbl_sql}("
            ddl += Config.NL
            ddl += columns
            ddl += Config.NL
            ddl += ")"
            ddl += Config.NL
            ddl += engine

            comment = (tbl.get("comment") or "").strip()
            if len(comment) > 0:
                ddl += Config.NL
                ddl += f"COMMENT '{comment}'"

            ddl += ";"

            if tbl_full in self.Grants.keys():
                ddl += Config.NL + Config.NL
                for grant in self.Grants.get(tbl_full):
                    ddl += grant + Config.NL

            if tbl_db not in self.Tables.keys():
                self.Tables[tbl_db] = {}
            self.Tables.get(tbl_db)[tbl_name] = ddl.strip()

    def GetViewsFixFunctions(self, view_ddl):
        result = ""

        for view_line in view_ddl.split(Config.NL):
            if view_line == "":
                result += view_line + Config.NL
                continue

            for fnc in self.Functions.values():
                fnc_params_masks = []
                fnc_params_map = {}

                fnc_def_split = re.split("({0})".format("|".join(fnc.Params)), fnc.Definition, flags=RE_FLAGS)

                for i, el in enumerate(fnc_def_split):
                    if el not in fnc.Params:
                        continue
                    if i == 0 or i == len(fnc_def_split)-1:
                        continue
                    fnc_params_masks.append([
                        el,
                        fnc_def_split[i-1],
                        fnc_def_split[i+1]
                    ])

                idx_start = 0
                idx_end = 0
                for prm in fnc_params_masks:
                    prm_name = prm[0]
                    prm_from = prm[1]
                    prm_to = prm[2]

                    if prm_to == "":
                        prm_to = " AS "

                    idx_start = view_line.find(prm_from, idx_end)
                    if idx_start < 0:
                        break
                    idx_start += len(prm_from)

                    idx_end = view_line.find(prm_to, idx_start)
                    if idx_end < 0:
                        break

                    fnc_params_map[prm_name] = view_line[idx_start:idx_end]

                if len(fnc_params_map) != len(fnc.Params):
                    continue

                fnc_def_old = fnc.Definition
                for prm, col in fnc_params_map.items():
                    if col.find(" ") >= 0:
                        fnc_def_old = fnc_def_old.replace(f" {prm}", f" ({prm})")
                    fnc_def_old = fnc_def_old.replace(prm, col)

                fnc_def_new = "{0}({1})".format(fnc.Name, ", ".join([fnc_params_map.get(i) for i in fnc.Params]))

                view_line = view_line.replace(fnc_def_old, fnc_def_new)

            result += view_line + Config.NL

        return result

    def GetViews(self):
        def Parse(is_mat, full_name, ddl):
            if is_mat:
                start_text = f"({Config.NL}    `"
                start_text_offset = 5
                end_text = f") AS{Config.NL}"
            else:
                start_text = f"CREATE VIEW {full_name}{Config.NL}({Config.NL}"
                start_text_offset = 0
                end_text = f"){Config.NL}AS ("

            start_ind = ddl.find(start_text)-start_text_offset
            if start_ind < 0:
                return ddl
            start_ind += len(start_text)-3

            end_idx = ddl.find(end_text, start_ind)
            if end_idx < 0:
                return ddl
            end_idx += 1

            ddl = ddl.replace(ddl[start_ind:end_idx], "")

            return ddl.replace(f"{Config.NL}AS (SELECT", f" AS({Config.NL}SELECT")

        self.Views = {}
        for view in self.GetData("""
            SELECT *
            FROM system.tables t
            WHERE
                t.engine in ('View','MaterializedView') and
                t.database not in ('INFORMATION_SCHEMA','information_schema','system')
        """):
            if view.get("engine") == "MaterializedView":
                type_name = "Materialized View"
                type_ddl = "MATERIALIZED VIEW"
                type_is_mat = True
            else:
                type_name = "View"
                type_ddl = "VIEW"
                type_is_mat = False

            view_db = view.get("database")
            if view_db not in self.Databases:
                continue

            view_name = view.get("name")
            view_full  = ".".join([view_db, self.QuoteName(view_name)])

            view_dfn = ""
            for row in self.GetData(f"SHOW CREATE {view_full}"):
                view_dfn = Parse(type_is_mat, view_full, row.get("statement"))

            view_dfn = self.GetViewsFixFunctions(view_dfn).strip()

            ddl = f"-- {type_name}: {view_full}"
            ddl += Config.NL + Config.NL
            ddl += f"-- DROP {type_ddl} IF EXISTS {view_full};"
            ddl += Config.NL + Config.NL
            ddl += view_dfn
            ddl += ";"

            if view_full in self.Grants.keys():
                ddl += Config.NL + Config.NL
                for grant in self.Grants.get(view_full):
                    ddl += grant + Config.NL

            if view_db not in self.Views.keys():
                self.Views[view_db] = {}
            self.Views.get(view_db)[view_name] = ddl.strip()

    def GetSettings(self):
        self.Settings = {}
        for row in self.GetData("SELECT * FROM system.settings"):
            self.Settings[row.get("name")] = row.get("value")

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
            ddl = "GRANT {0} TO {1};".format(role_child, role_parent)

            if role_parent not in self.RoleGrants.keys():
                self.RoleGrants[role_parent] = []
            self.RoleGrants.get(role_parent).append(ddl)

            if role_child not in self.RoleGrants.keys():
                self.RoleGrants[role_child] = []
            self.RoleGrants.get(role_child).append(ddl)

    def GetGrants(self):
        self.Grants = {}
        for row in self.GetData("""
            SELECT
                COALESCE(g.role_name, g.user_name) AS role_name,
                g.access_type,
                g.database,
                g.table,
                g.grant_option
            FROM system.grants g
            order by 1,2,3,4
        """):
            role_name = (row.get("role_name") or "").strip()
            access_type = (row.get("access_type") or "").strip().upper()
            database = (row.get("database") or "*").strip()
            table = (row.get("table") or "*").strip()
            grant_option = " WITH GRANT OPTION" if (row.get("grant_option") or 0) == 1 else ""

            if len(role_name) <= 0:
                continue

            column = (row.get("column") or "").strip()
            if len(column) > 0:
                column = f"{column}"

            ddl = f"GRANT {access_type}{column} ON {database}.{table} TO {role_name}{grant_option};"

            if role_name not in self.Grants.keys():
                self.Grants[role_name] = []
            self.Grants[role_name].append(ddl)

            role_name = f"{database}.{table}"
            if role_name not in self.Grants.keys():
                self.Grants[role_name] = []
            self.Grants[role_name].append(ddl)

    def GetRoles(self):
        self.Roles = {}
        for row in self.GetData("SELECT * FROM system.roles"):
            role_name = row.get("name")

            ddl = "-- Role: {0}".format(role_name)
            ddl += Config.NL + Config.NL
            ddl += "-- DROP ROLE IF EXISTS {0};".format(role_name)
            ddl += Config.NL + Config.NL
            ddl += "CREATE ROLE {0};".format(role_name)
            ddl += Config.NL + Config.NL

            has_grant = True
            for grant in sorted(self.Grants.get(role_name) or []):
                ddl += grant
                ddl += Config.NL
                has_grant = True

            if has_grant:
                ddl += Config.NL

            for grant in sorted(self.RoleGrants.get(role_name) or []):
                ddl += grant
                ddl += Config.NL

            self.Roles[role_name] = ddl.strip() + Config.NL

    def GetUsers(self):
        self.Users = {}

        for row in self.GetData("SELECT * FROM system.users"):
            user_name = row.get("name")
            auth_type = row.get("auth_type") or []
            auth_params = row.get("auth_params") or []

            ddl = f"-- User: {user_name}"
            ddl += Config.NL + Config.NL
            ddl += f"-- DROP USER IF EXISTS {user_name};"
            ddl += Config.NL + Config.NL
            ddl += f"CREATE USER {user_name}"
            ddl += Config.NL

            if len(auth_type) <= 0:
                ddl += "  NOT IDENTIFIED"
            else:
                for i, at in enumerate(auth_type):
                    if i >= len(auth_params):
                        continue
                    ap = auth_params[i].strip().lower()
                    at = at.strip().lower()

                    if at == "ldap" and ap not in ("", "{}"):
                        server = json.loads(ap).get("server")
                        ddl += f"  IDENTIFIED WITH {at} SERVER '{server}'"
                    else:
                        ddl += f"  IDENTIFIED WITH {at}"

            ddl += ';' + Config.NL + Config.NL

            has_grant = False
            for grant in sorted(self.Grants.get(user_name) or []):
                ddl += grant
                ddl += Config.NL
                has_grant = True

            if has_grant:
                ddl += Config.NL

            for grant in sorted(self.RoleGrants.get(user_name) or []):
                ddl += grant
                ddl += Config.NL

            if user_name in self.UserSettings.keys():
                ddl += f"alter user {user_name} settings"
                ddl += ", ".join([f"{Config.NL}  {k} = {v}" for k,v in self.UserSettings.get(user_name).items()])
                ddl += ";" + Config.NL

            self.Users[user_name] = ddl.strip() + Config.NL

    def GetUserSettings(self):
        self.UserSettings = {}
        for row in self.GetData("""
            select *
            from system.settings_profile_elements e
            where
                e.user_name is not null and
                e.setting_name is not null and
                e.value is not null
        """):
            user_name = row.get("user_name")
            key = row.get("setting_name")
            val = row.get("value")
            if user_name not in self.UserSettings.keys():
                self.UserSettings[user_name] = {}
            self.UserSettings.get(user_name)[key] = val

    def GetFunctions(self):
        self.Functions = {}
        for row in self.GetData("""
            select *
            from system.functions f
            where f.origin NOT IN ('System')
        """):
            fnc = Function(row)
            self.Functions[fnc.Name] = fnc

    def GetDictionaries(self):
        self.Dictionaries = {}
        for row in self.GetData("""
            select *
            from system.tables f
            where f.engine in ('Dictionary')
        """):
            db = row.get("database")
            name = row.get("name")
            name_full = ".".join([db, self.QuoteName(name)])

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

        # Create result path
        if not os.path.exists(path):
            os.mkdir(path)

        # Tables
        for db in self.Tables.keys():
            path_db = os.path.join(path, db)
            if not os.path.exists(path_db):
                os.mkdir(path_db)

            path_tables = os.path.join(path_db, "tables")
            if not os.path.exists(path_tables):
                os.mkdir(path_tables)

            for tbl_name, tbl_ddl in (self.Tables.get(db) or {}).items():
                files.append([
                    os.path.join(path_tables, f"{tbl_name}.sql"),
                    tbl_ddl
                ])

        # Views
        for db in self.Views.keys():
            path_db = os.path.join(path, db)
            if not os.path.exists(path_db):
                os.mkdir(path_db)

            path_views = os.path.join(path_db, "views")
            if not os.path.exists(path_views):
                os.mkdir(path_views)

            for view_name, view_ddl in (self.Views.get(db) or {}).items():
                files.append([
                    os.path.join(path_views, f"{view_name}.sql"),
                    view_ddl
                ])

        # Dictionaries
        for db in self.Dictionaries.keys():
            path_db = os.path.join(path, db)
            if not os.path.exists(path_db):
                os.mkdir(path_db)

            path_dicts = os.path.join(path_db, "dicts")
            if not os.path.exists(path_dicts):
                os.mkdir(path_dicts)

            for name, ddl in (self.Dictionaries.get(db) or {}).items():
                files.append([
                    os.path.join(path_dicts, f"{name}.sql"),
                    ddl
                ])

        # Roles
        path_roles = os.path.join(path, "roles")
        if not os.path.exists(path_roles):
            os.mkdir(path_roles)
        for role_name, role_ddl in self.Roles.items():
            files.append([
                os.path.join(path_roles, f"{role_name}.sql"),
                role_ddl
            ])

        # Users
        path_users = os.path.join(path, "users")
        if not os.path.exists(path_users):
            os.mkdir(path_users)
        for user_name, user_ddl in self.Users.items():
            files.append([
                os.path.join(path_users, f"{user_name}.sql"),
                user_ddl
            ])

        # Functions
        path_fnc = os.path.join(path, "functions")
        if not os.path.exists(path_fnc):
            os.mkdir(path_fnc)

        for name, fnc in self.Functions.items():
            files.append([
                os.path.join(path_fnc, f"{name}.sql"),
                fnc.GetDDL()
            ])

        # Write to disc
        with Pool(processes=Config.Threads) as pool:
            pool.map(self.WriteFile, files)

        # Settings
        self.WriteFile([
            os.path.join(path, "settings.json"),
            json.dumps(self.Settings, ensure_ascii=False, indent=2, sort_keys=True)
        ])

    def WriteFile(self, prm):
        with open(prm[0], 'w', encoding="utf-8") as wf:
            wf.write(prm[1])
