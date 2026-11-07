from .channels import resolve


class Session:
    def __init__(self, names, units, rows, source="<memory>"):
        self.source = source
        self.raw_names = list(names)
        mapping = resolve(self.raw_names)
        self.columns = {}
        self.units = {}
        for key, idxs in mapping.items():
            col = []
            for row in rows:
                vals = [row[i] for i in idxs if i < len(row) and row[i] is not None]
                col.append(sum(vals) / len(vals) if vals else None)
            self.columns[key] = col
            self.units[key] = units[idxs[0]] if idxs[0] < len(units) else ""

    def has(self, key):
        return key in self.columns and any(v is not None for v in self.columns[key])

    def col(self, key):
        return self.columns.get(key, [])

    def __len__(self):
        return max((len(c) for c in self.columns.values()), default=0)
