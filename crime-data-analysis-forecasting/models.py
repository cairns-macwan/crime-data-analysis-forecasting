
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, Float, Text

class Base(DeclarativeBase):
    pass

class Location(Base):
    __tablename__ = "app_locations"   # ← renamed
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    area: Mapped[str] = mapped_column(String(120), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    crimes = relationship("Crime", back_populates="location")

class Crime(Base):
    __tablename__ = "app_crimes"      # ← renamed
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crime_type: Mapped[str] = mapped_column(String(120), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM
    outcome: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("app_locations.id"), index=True)  # ← updated FK
    location = relationship("Location", back_populates="crimes")
