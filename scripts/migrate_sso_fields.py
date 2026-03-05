"""数据库迁移脚本：添加SSO字段"""

import sys
sys.path.insert(0, '.')

from src.storage.db.manager import db_manager
from sqlalchemy import text

def run_migration():
    """运行数据库迁移"""
    engine = db_manager.engine
    
    sql_statements = [
        'ALTER TABLE users ADD COLUMN external_user_id VARCHAR(64)',
        'ALTER TABLE users ADD COLUMN external_token VARCHAR(256)',
        'ALTER TABLE users ADD COLUMN external_roles JSON',
        'ALTER TABLE users ADD COLUMN sso_last_login DATETIME',
    ]
    
    with engine.connect() as conn:
        for sql in sql_statements:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f'SUCCESS: {sql}')
            except Exception as e:
                error_msg = str(e).lower()
                if 'duplicate column' in error_msg or 'already exists' in error_msg:
                    print(f'SKIP (already exists): {sql}')
                else:
                    print(f'FAILED: {sql} - {e}')
    
    print('Migration completed.')

if __name__ == '__main__':
    run_migration()
