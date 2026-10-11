import os
from datetime import datetime

from flask import Flask, request
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, DateTime, String
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------- Переменные окружения ----------
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ---------- SQLAlchemy ----------
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ---------- Модель Visit ----------
class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True)
    visited_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=False)


# ---------- Создание таблицы при старте ----------
Base.metadata.create_all(bind=engine)

# ---------- Flask-приложение ----------
app = Flask(__name__)


@app.route("/hello")
def hello():
    session = SessionLocal()
    session.add(Visit(visited_at=datetime.utcnow(), ip_address=request.remote_addr))
    session.commit()
    session.close()
    return "Hello", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
