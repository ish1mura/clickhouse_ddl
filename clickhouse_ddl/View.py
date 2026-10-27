import re

from clickhouse_ddl.Config import Config
from clickhouse_ddl.System import QuoteName, RE_FLAGS

class View:
    def __init__(self, data):
        if data.get("engine") == "MaterializedView":
            self.TypeName = "Materialized View"
            self.TypeDDL = "MATERIALIZED VIEW"
            self.IsMaterialized = True
        else:
            self.TypeName = "View"
            self.TypeDDL = "VIEW"
            self.IsMaterialized = False

        self.DB = data.get("database")

        self.Name = data.get("name")

        self.NameFull = ".".join([self.DB, QuoteName(self.Name)])

        self.Comment = (data.get("comment") or "").strip()

        self.Definition = ""

        self.Grants = {}

    def GetDDL(self):
        ddl = f"-- {self.TypeName}: {self.NameFull}"
        ddl += Config.NL + Config.NL
        ddl += f"-- DROP {self.TypeDDL} IF EXISTS {self.NameFull};"
        ddl += Config.NL + Config.NL
        ddl += self.Definition

        if len(self.Comment) > 0:
            ddl += Config.NL
            ddl += f"COMMENT '{self.Comment}'"

        ddl += ";"

        if len(self.Grants) > 0:
            ddl += Config.NL + Config.NL
            for grant in self.Grants:
                ddl += grant + Config.NL

        return ddl.strip() + Config.NL

    def SetDDL(self, ddl, functions):
        if self.IsMaterialized:
            start_text = f"({Config.NL}    `"
            start_text_offset = 5
            end_texts = [
                f") AS{Config.NL}",
                f"' AS{Config.NL}",
            ]
        else:
            start_text = f"CREATE VIEW {self.NameFull}{Config.NL}({Config.NL}"
            start_text_offset = 0
            end_texts = [
                f"){Config.NL}AS (",
                f"'{Config.NL}AS (",
                f"){Config.NL}AS ",
                f"'{Config.NL}AS ",
            ]

        start_ind = ddl.find(start_text)-start_text_offset
        if start_ind < 0:
            return ddl
        start_ind += len(start_text)-3

        for end_text in end_texts:
            end_idx = ddl.find(end_text, start_ind)
            if end_idx >= 0:
                break
        if end_idx < 0:
            return ddl
        end_idx += 1

        ddl = ddl.replace(ddl[start_ind:end_idx], "")

        ddl = ddl.replace(f"{Config.NL}AS (SELECT", f" AS({Config.NL}SELECT")

        ddl = ddl.replace(f"{Config.NL}AS SELECT", f" AS{Config.NL}SELECT")

        ddl = ddl.strip()

        self.Definition = self.SetDDLFixFunctions(ddl, functions)

    def SetDDLFixFunctions(self, ddl, functions):
        result = ""

        for view_line in ddl.split(Config.NL):
            if view_line == "":
                result += view_line + Config.NL
                continue

            for fnc in functions:
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

        return result.strip()
