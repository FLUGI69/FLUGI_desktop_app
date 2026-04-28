import sqlalchemy

from sqlalchemy import (
    Table, Column, Integer, String, Text,
    BigInteger, VARCHAR, Boolean, DateTime, TEXT
)

class SetupTables:

    def audit_log(tablebase, tablename: str, sqlType = "mysql", unified_table = False):

        class audit_log_table:

            __tablename__ = tablename

            id = Column(BigInteger() if sqlType == "mysql" else Integer(), autoincrement = True, primary_key = True, nullable = False)

            if unified_table == True:
                table_name = Column(VARCHAR(255), nullable = False)

            row_id = Column(BigInteger() if sqlType == "mysql" else Integer(), nullable = False)

            column_name = Column(VARCHAR(255), nullable = False)

            dml_type = Column(VARCHAR(255), nullable = False)

            old_value = Column(TEXT(255), nullable = True)

            new_value = Column(TEXT(255), nullable = True)

            done_by = Column(VARCHAR(255), nullable = False)

            done_at = Column(DateTime, nullable = False)

        namespace = {"audit_log_table": audit_log_table, "tablebase": tablebase}
        
        exec("class %s(audit_log_table, tablebase):\n\tpass" % str(tablename), namespace)
        
        return namespace[tablename]