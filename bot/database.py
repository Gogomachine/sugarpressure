import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class PressureReading(Base):
    __tablename__ = "pressure_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    systolic = Column(Integer, nullable=False)
    diastolic = Column(Integer, nullable=False)
    pulse = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class GlucoseReading(Base):
    __tablename__ = "glucose_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


engine = create_engine("sqlite:///health_diary.db", echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def add_pressure(user_id: int, systolic: int, diastolic: int, pulse: int | None = None) -> PressureReading:
    session = Session()
    reading = PressureReading(
        user_id=user_id,
        systolic=systolic,
        diastolic=diastolic,
        pulse=pulse,
    )
    session.add(reading)
    session.commit()
    session.refresh(reading)
    session.close()
    return reading


def add_glucose(user_id: int, value: float) -> GlucoseReading:
    session = Session()
    reading = GlucoseReading(user_id=user_id, value=value)
    session.add(reading)
    session.commit()
    session.refresh(reading)
    session.close()
    return reading


def get_pressure_history(user_id: int, days: int = 30) -> list[PressureReading]:
    session = Session()
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    readings = (
        session.query(PressureReading)
        .filter(PressureReading.user_id == user_id, PressureReading.timestamp >= since)
        .order_by(PressureReading.timestamp)
        .all()
    )
    session.close()
    return readings


def delete_reading(user_id: int, reading_type: str, reading_id: int) -> bool:
    """Delete a reading by type ('pressure' or 'glucose') and id. Returns True if deleted."""
    model = PressureReading if reading_type == "pressure" else GlucoseReading
    session = Session()
    reading = session.query(model).filter(model.id == reading_id, model.user_id == user_id).first()
    if reading:
        session.delete(reading)
        session.commit()
        session.close()
        return True
    session.close()
    return False


def get_glucose_history(user_id: int, days: int = 30) -> list[GlucoseReading]:
    session = Session()
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    readings = (
        session.query(GlucoseReading)
        .filter(GlucoseReading.user_id == user_id, GlucoseReading.timestamp >= since)
        .order_by(GlucoseReading.timestamp)
        .all()
    )
    session.close()
    return readings
