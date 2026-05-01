import sys
import os
from unittest.mock import MagicMock

# Dummy class for typing imports to avoid SyntaxError with MagicMock
class DummyClass:
    pass

class DummyDeclarativeBase:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class DummyEnum(str):
    pass

# Create a mock for pandas
class MockPandas(MagicMock):
    pass

class MockDataFrame(MagicMock):
    @property
    def empty(self):
        return False

mock_pd = MockPandas()
mock_pd.DataFrame = MockDataFrame
sys.modules['pandas'] = mock_pd

# Create a mock for sqlalchemy
class MockSQLAlchemy(MagicMock):
    pass

mock_sqlalchemy = MockSQLAlchemy()
mock_sqlalchemy.Column = MagicMock()
mock_sqlalchemy.Integer = MagicMock()
mock_sqlalchemy.String = MagicMock()
mock_sqlalchemy.Numeric = MagicMock()
mock_sqlalchemy.Date = MagicMock()
mock_sqlalchemy.DateTime = MagicMock()
mock_sqlalchemy.Enum = MagicMock()
mock_sqlalchemy.ForeignKey = MagicMock()

sys.modules['sqlalchemy'] = mock_sqlalchemy

mock_orm = MagicMock()
mock_orm.declarative_base = lambda: DummyDeclarativeBase
mock_orm.relationship = MagicMock()
mock_orm.Session = MagicMock()
sys.modules['sqlalchemy.orm'] = mock_orm
sys.modules['sqlalchemy.ext.declarative'] = MagicMock()

# Create a mock for yfinance
sys.modules['yfinance'] = MagicMock()

# Create a mock for defusedxml
sys.modules['defusedxml'] = MagicMock()
sys.modules['defusedxml.ElementTree'] = MagicMock()

# Create a mock for httpx
sys.modules['httpx'] = MagicMock()

# Create a mock for tefas
sys.modules['tefas'] = MagicMock()

# Append to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
