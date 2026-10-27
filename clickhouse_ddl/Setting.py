class Setting:
    def __init__(self, data):
        self.Name = data.get("name")

        self.Value = (data.get("value") or "").strip()
        self.ValueDefault = (data.get("default") or "").strip()

        self.Comment = (data.get("description") or "").strip()

        self.IsChanged = (data.get("changed") or 0) > 0

    def GetDDL(self):
        default = f"# '{self.ValueDefault}'" if self.Value != self.ValueDefault else ""
        return f"{self.Name} = '{self.Value}' {default}".strip()
