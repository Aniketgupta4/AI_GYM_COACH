import sqlite3
import streamlit as st
from pathlib import Path

_DB_PATH = str(Path(__file__).parent.parent.parent / "data.db")


@st.cache_resource
def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _get_connection()

    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exercises (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(id),
                exercise_name TEXT    NOT NULL,
                reps          INTEGER NOT NULL DEFAULT 0,
                sets          INTEGER NOT NULL DEFAULT 0,
                time          INTEGER NOT NULL DEFAULT 0,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def get_user(username: str) -> sqlite3.Row:
    conn = _get_connection()

    return conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()


def create_user(username: str) -> sqlite3.Row:
    conn = _get_connection()
    
    with conn:
        conn.execute(
            "INSERT INTO users (username) VALUES (?)", (username,)
        )

    return get_user(username) 


def get_or_create_user(username: str) -> sqlite3.Row:
    user = get_user(username)

    if user is None:
        user = create_user(username)
    
    return user


def add_exercise(user_id, exercise_name, reps, sets, time_seconds):
    """
    Save a completed workout session to the database.
    Each finished session is recorded as a distinct entry with local timestamp.
    """
    if not user_id or reps <= 0:
        return

    conn = _get_connection()

    with conn:
        conn.execute(
            """
            INSERT INTO exercises (user_id, exercise_name, sets, reps, time, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """,
            (user_id, exercise_name, max(0, int(sets)), max(1, int(reps)), max(1, round(float(time_seconds))))
        )


def get_users_exercises(user_id):
    """
    Retrieve all workout sessions for a given user, newest first.
    """
    conn = _get_connection()

    return conn.execute(
        """
        SELECT id, user_id, exercise_name, reps, sets, time, created_at 
        FROM exercises 
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()


def clear_user_history(user_id):
    """
    Clear workout history for a user.
    """
    conn = _get_connection()
    with conn:
        conn.execute("DELETE FROM exercises WHERE user_id = ?", (user_id,))