from __future__ import annotations

from typing import Tuple

from sqlalchemy import BigInteger, Column, Integer, String, func

from database import database, session

class UserStats(database.base):
    """User points for reactions and messages ..."""

    __tablename__ = "boards_points_users"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger)
    user_id = Column(BigInteger)
    points  = Column(Integer)
    
    @staticmethod
    def get_stats(guild_id: int, user_id: int) -> PointsUser:
        """Get user stats."""
        query = (
            session.query(UserStats)
            .filter_by(
                guild_id=guild_id,
                user_id=user_id,
            )
            .one_or_none()
        )
        return query
        
    @staticmethod
    def increment(guild_id: int, user_id: int, value: int):
        query = session.query(UserStats).filter_by(guild_id=guild_id, user_id=user_id).first()
        
        if not query:
            query = UserStats(
                guild_id=guild_id,
                user_id=user_id,
                points=0
            )
        else:
            query.points += value
            
        session.merge(query)
        session.commit()

        
    @staticmethod
    def get_position(guild_id: int, points: int) -> int:
        result = (
            session.query(func.count(UserStats.user_id))
            .filter_by(guild_id=guild_id)
            .filter(getattr(UserStats, "points") > points)
            .one_or_none()
        )
        return result[0] + 1 if result else None
        
        return query
        
    @staticmethod
    def get_best(guild_id: int, order: str, limit: int = 10, offset: int = 0):
        if order == "desc":
            order = UserStats.points.desc()
        elif order == "asc":
            order = UserStats.points.asc()
        else:
            raise Exception("Invalid order: " + order)
            
        return session.query(UserStats).filter_by(guild_id=guild_id).order_by(order).offset(offset).limit(limit)

    def save(self):
        session.commit()

    def __repr__(self) -> str:
        return (
            f'<Relation idx="{self.idx}" guild_id="{self.guild_id}" '
            f'user_id="{self.user_id}" points="{self.points}">'
        )

    def dump(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "points": self.points
        }