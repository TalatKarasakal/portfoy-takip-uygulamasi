import sys
from unittest.mock import MagicMock
import json

# Dummy Read Excel logic
class DummyPandas:
    def DataFrame(self, data, *args, **kwargs):
        class DummyDF:
            def __init__(self, d):
                if isinstance(d, list) and len(d) > 0 and isinstance(d[0], dict):
                    # convert list of dicts to dict of lists
                    self.columns = list(d[0].keys())
                    self._d = {col: [row.get(col) for row in d] for col in self.columns}
                elif isinstance(d, dict):
                    self.columns = list(d.keys())
                    self._d = d
                else:
                    self.columns = []
                    self._d = {}

            @property
            def empty(self):
                return len(self.columns) == 0 or len(self._d.get(self.columns[0], [])) == 0

            def to_excel(self, path, *a, **kw):
                with open(str(path) + '.json', 'w') as f:
                    json.dump(self._d, f, default=str)

            def iterrows(self):
                if not self._d or len(self.columns) == 0: return []
                n_rows = len(self._d[self.columns[0]])
                for i in range(n_rows):
                    row = {k: self._d[k][i] for k in self.columns}
                    class RowWrapper:
                        def __init__(self, row_dict):
                            self.d = row_dict
                        def get(self, key, default=None):
                            return self.d.get(key, default)
                        def __getitem__(self, key):
                            return self.d[key]
                    yield i, RowWrapper(row)

            def sort_values(self, *args, **kwargs):
                return self

            def head(self, *args, **kwargs):
                return self

            @property
            def iloc(self):
                class ILocHelper:
                    def __init__(self, df_dict, columns):
                        self._d = df_dict
                        self.columns = columns
                    def __getitem__(self, index):
                        if isinstance(index, int):
                            row = {k: self._d[k][index] for k in self.columns}
                            class RowWrapper:
                                def __init__(self, row_dict):
                                    self.d = row_dict
                                def __getitem__(self, key):
                                    return self.d[key]
                            return RowWrapper(row)
                        return self
                return ILocHelper(self._d, self.columns)

        return DummyDF(data)

    def ExcelWriter(self, *args, **kwargs):
        class DummyWriter:
            def __enter__(self): return self
            def __exit__(self, *a): pass
        return DummyWriter()

    def isna(self, val):
        return val in [None, 'NAN']

    def read_excel(self, file_path, sheet_name=None):
        import json
        with open(str(file_path) + '.json', 'r') as f:
            data = json.load(f)
        return {"Sheet1": self.DataFrame(data)}

    class Timestamp:
        def __init__(self, *args, **kwargs): pass
        def __str__(self): return "2023-10-10"

sys.modules['pandas'] = DummyPandas()

# Mock for missing sqlalchemy
def DummyColumn(*args, **kwargs):
    return MagicMock()

def DummyInteger(*args, **kwargs): return MagicMock()
def DummyForeignKey(*args, **kwargs): return MagicMock()
def DummyEnum(*args, **kwargs): return MagicMock()
def DummyDate(*args, **kwargs): return MagicMock()
def DummyNumeric(*args, **kwargs): return MagicMock()
def DummyString(*args, **kwargs): return MagicMock()
def DummyDateTime(*args, **kwargs): return MagicMock()

class DummySQLAlchemy:
    Column = DummyColumn
    Integer = DummyInteger
    ForeignKey = DummyForeignKey
    Enum = DummyEnum
    Date = DummyDate
    Numeric = DummyNumeric
    String = DummyString
    DateTime = DummyDateTime

class DummySQLAlchemyORM:
    def declarative_base(self):
        class Base:
            def __init__(self, *args, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        return Base
    def relationship(self, *args, **kwargs): return MagicMock()
    def sessionmaker(self, *args, **kwargs): return MagicMock()
    class Session: pass

    def joinedload(self, *args, **kwargs): pass

sys.modules['sqlalchemy'] = DummySQLAlchemy()
sys.modules['sqlalchemy.orm'] = DummySQLAlchemyORM()
sys.modules['sqlalchemy.ext.declarative'] = MagicMock()

# Mock for missing PySide6
sys.modules['PySide6'] = MagicMock()
sys.modules['PySide6.QtCore'] = MagicMock()
sys.modules['PySide6.QtGui'] = MagicMock()
sys.modules['PySide6.QtWidgets'] = MagicMock()
sys.modules['PySide6.QtCharts'] = MagicMock()

# Mock for missing yfinance
sys.modules['yfinance'] = MagicMock()

# Mock for missing defusedxml
sys.modules['defusedxml'] = MagicMock()
sys.modules['defusedxml.ElementTree'] = MagicMock()

# Mock for missing httpx
sys.modules['httpx'] = MagicMock()

# Mock for missing tefas
sys.modules['tefas'] = MagicMock()
