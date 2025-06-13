import sqlite3
from command import Command


class DBService:
    def __init__(self, db_name="commands.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.init_db()

    def init_db(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS commands
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             name TEXT NOT NULL,
                             command TEXT NOT NULL,
                             notes TEXT)"""
            )
            self.conn.commit()
        except Exception as e:
            raise Exception(f"无法初始化数据库: {str(e)}")

    def save_command(self, command_obj):
        self.cursor.execute(
            "INSERT INTO commands (name, command, notes) VALUES (?, ?, ?)",
            (command_obj.name, command_obj.command, command_obj.notes),
        )
        self.conn.commit()

    def get_commands(self) -> list[Command]:
        self.cursor.execute("SELECT id, name, command, notes FROM commands")
        return [
            Command(id=row[0], name=row[1], command=row[2], notes=row[3])
            for row in self.cursor.fetchall()
        ]

    def update_command(self, command_obj):
        self.cursor.execute(
            "UPDATE commands SET name=?, command=?, notes=? WHERE id=?",
            (command_obj.name, command_obj.command, command_obj.notes, command_obj.id),
        )
        self.conn.commit()

    def delete_commands(self, command_ids):
        """
        批量删除命令
        :param command_ids: 要删除的命令ID列表
        """
        if not command_ids:
            return

        # 使用IN语句批量删除
        placeholders = ",".join(["?"] * len(command_ids))
        sql = f"DELETE FROM commands WHERE id IN ({placeholders})"

        try:
            self.cursor.execute(sql, command_ids)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"批量删除命令失败: {str(e)}")

    def close(self):
        if self.conn:
            self.conn.close()

    def delete_command(self, command_id):
        self.cursor.execute("DELETE FROM commands WHERE id=?", (command_id,))
        self.conn.commit()
