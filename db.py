from pathlib import Path
import os
import sqlite3
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(exist_ok=True)
SQLITE_PATH = DB_DIR / "escolta.db"


def get_database_url() -> str:
    try:
        return st.secrets.get("DATABASE_URL", "") or os.getenv("DATABASE_URL", "")
    except Exception:
        return os.getenv("DATABASE_URL", "")


def using_postgres() -> bool:
    return bool(get_database_url())


class CursorWrapper:
    def __init__(self, cursor, is_postgres=False):
        self._cursor = cursor
        self._is_postgres = is_postgres

    def _adapt_sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self._is_postgres else sql

    def execute(self, sql, params=None):
        sql = self._adapt_sql(sql)
        if params is None:
            self._cursor.execute(sql)
        else:
            self._cursor.execute(sql, params)
        return self

    def executemany(self, sql, params_seq):
        sql = self._adapt_sql(sql)
        self._cursor.executemany(sql, params_seq)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class ConnectionWrapper:
    def __init__(self, conn, is_postgres=False):
        self._conn = conn
        self._is_postgres = is_postgres

    def cursor(self):
        return CursorWrapper(self._conn.cursor(), self._is_postgres)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_connection():
    database_url = get_database_url()
    if database_url:
        try:
            import psycopg
            from psycopg.rows import dict_row
            conn = psycopg.connect(database_url, row_factory=dict_row)
            return ConnectionWrapper(conn, is_postgres=True)
        except Exception as e:
            raise RuntimeError(f"Erro ao conectar no banco online: {e}")

    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return ConnectionWrapper(conn, is_postgres=False)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    if using_postgres():
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            usuario TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL,
            ativo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS agentes (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            telefone TEXT,
            pix TEXT,
            observacao TEXT,
            ativo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS rotas (
            id SERIAL PRIMARY KEY,
            nome_rota TEXT NOT NULL,
            origem TEXT,
            destino TEXT,
            valor_fixo_receber NUMERIC DEFAULT 0,
            valor_fixo_pagar NUMERIC DEFAULT 0,
            observacao TEXT,
            ativa INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS servicos (
            id SERIAL PRIMARY KEY,
            data_servico TEXT NOT NULL,
            rota_id INTEGER NOT NULL,
            agente_id INTEGER NOT NULL,
            placa_caminhao TEXT,
            hora_inicial TEXT,
            hora_final TEXT,
            total_horas NUMERIC DEFAULT 0,
            valor_fixo_receber NUMERIC DEFAULT 0,
            valor_fixo_pagar NUMERIC DEFAULT 0,
            valor_extra_recebido NUMERIC DEFAULT 0,
            pedagio_km_extra NUMERIC DEFAULT 0,
            total_receber NUMERIC DEFAULT 0,
            total_pagar NUMERIC DEFAULT 0,
            lucro NUMERIC DEFAULT 0,
            observacao TEXT,
            status_pagamento TEXT DEFAULT 'pendente',
            data_pagamento TEXT,
            forma_pagamento TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL,
            ativo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS agentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            pix TEXT,
            observacao TEXT,
            ativo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS rotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_rota TEXT NOT NULL,
            origem TEXT,
            destino TEXT,
            valor_fixo_receber REAL DEFAULT 0,
            valor_fixo_pagar REAL DEFAULT 0,
            observacao TEXT,
            ativa INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_servico TEXT NOT NULL,
            rota_id INTEGER NOT NULL,
            agente_id INTEGER NOT NULL,
            placa_caminhao TEXT,
            hora_inicial TEXT,
            hora_final TEXT,
            total_horas REAL DEFAULT 0,
            valor_fixo_receber REAL DEFAULT 0,
            valor_fixo_pagar REAL DEFAULT 0,
            valor_extra_recebido REAL DEFAULT 0,
            pedagio_km_extra REAL DEFAULT 0,
            total_receber REAL DEFAULT 0,
            total_pagar REAL DEFAULT 0,
            lucro REAL DEFAULT 0,
            observacao TEXT,
            status_pagamento TEXT DEFAULT 'pendente',
            data_pagamento TEXT,
            forma_pagamento TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

    conn.commit()

    row = cur.execute("SELECT COUNT(*) AS total FROM usuarios").fetchone()
    total = int(row["total"] or 0)
    if total == 0:
        cur.execute(
            "INSERT INTO usuarios (nome, usuario, senha, perfil, ativo) VALUES (?, ?, ?, ?, ?)",
            ("Administrador", "admin", "admin123", "admin", 1),
        )
        conn.commit()

    conn.close()
