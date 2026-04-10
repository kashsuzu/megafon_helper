from contextlib import asynccontextmanager
from pathlib import Path
from typing import Iterable

import aiosqlite
from loguru import logger

from config import DATABASE_FILE_NAME
from src.megafon.datatypes import MegafonAccountData


class Database:
    def __init__(
        self,
        db_path: str = DATABASE_FILE_NAME,
    ) -> None:
        self.db_path = db_path

    @asynccontextmanager
    async def _establish_connection(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                yield db
        except Exception as err:
            logger.error(
                f"Не удалось подключиться к базе данных! Error:\n{err}"
            )

    async def create_tables(self) -> None:
        async with self._establish_connection() as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS accounts (
                                account_id INTEGER PRIMARY KEY,
                                owner_id INTEGER NOT NULL,
                                access_token TEXT DEFAULT '',
                                refresh_token TEXT DEFAULT '',
                                cookies TEXT DEFAULT '{}',
                                number TEXT DEFAULT '',
                                proxies TEXT DEFAULT '',
                                last_activate_datetime INTEGER DEFAULT 1,
                                pin TEXT DEFAULT '0000',
                                formated_number TEXT DEFAULT ''
                             )""")
            await db.commit()
            logger.info("Таблицы успешно созданы")

    async def get_accounts_by_owner_id(self, owner_id: int) -> Iterable:
        async with self._establish_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM accounts WHERE owner_id = ?", (owner_id,)
            )
            return await cursor.fetchall()

    async def add_account(self, owner_id: int) -> int:
        async with self._establish_connection() as db:
            cursor = await db.execute(
                "INSERT INTO accounts (owner_id) VALUES (?) RETURNING account_id",
                (owner_id,),
            )
            account_id_row = await cursor.fetchone()
            await db.commit()
            logger.info("Аккаунт успешно добавлен в базу данных")

            return account_id_row[0]  # type: ignore

    async def update_account_data(
        self, account_data: MegafonAccountData
    ) -> None:
        logger.debug("Записываю данные аккаунта в базу данных")
        account_data = account_data.get_data_for_db()
        async with self._establish_connection() as db:
            await db.execute(
                """
                UPDATE accounts
                SET
                    access_token = ?,
                    refresh_token = ?,
                    cookies = ?,
                    proxies = ?,
                    last_activate_datetime = ?,
                    number = ?,
                    formated_number= ?
                WHERE account_id = ?
                """,
                (
                    account_data.access_token,
                    account_data.refresh_token,
                    account_data.cookies,
                    account_data.proxies,
                    account_data.last_activate_datetime,
                    account_data.number,
                    account_data.formated_number,
                    account_data.account_id,
                ),
            )
            await db.commit()
            logger.info("Данные аккаунта успешно обновлены в базе данных")

    async def delete_account(self, account_id: int) -> None:
        async with self._establish_connection() as db:
            await db.execute(
                "DELETE FROM accounts WHERE account_id = ?", (account_id,)
            )
            await db.commit()
            logger.info("Аккаунт успешно удалён из базы данных")
