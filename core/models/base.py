from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime,Date,ForeignKey,Boolean,Enum,Table,JSON
from sqlalchemy import Text as SQLText
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

# Keep model imports configuration-free and let SQLAlchemy select the concrete
# type per engine.  The previous import-time cfg fallback chose MEDIUMTEXT when
# config.yaml was absent, which made the same metadata impossible to compile on
# SQLite or PostgreSQL.
Text = SQLText().with_variant(MEDIUMTEXT(), "mysql")

class DataStatus():
    DELETED:int = 1000
    ACTIVE:int = 1
    INACTIVE:int = 2
    PENDING:int = 3
    COMPLETED:int = 4
    FAILED:int = 5
    FETCHING:int = 6  # 正在获取内容（锁定状态，防止多节点重复获取）
DATA_STATUS=DataStatus()
Base = declarative_base()
