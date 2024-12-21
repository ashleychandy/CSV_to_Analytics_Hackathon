from sqlalchemy.orm import Session
from src.models.user import User
from src.utils.auth import get_password_hash

class UserRepository:
    """Repository for user operations."""

    def __init__(self, db: Session = None):
        """Initialize repository with database session."""
        self.db = db
        self._initialize_test_users()

    def _initialize_test_users(self):
        """Initialize test users if they don't exist."""
        if not self.db:
            return
            
        # Check if users exist
        if self.db.query(User).count() == 0:
            # Create test users
            test_users = [
                User(
                    username="user1",
                    password_hash=get_password_hash("pass1"),
                    role="user"
                ),
                User(
                    username="user2",
                    password_hash=get_password_hash("pass2"),
                    role="user"
                ),
                User(
                    username="user3",
                    password_hash=get_password_hash("pass3"),
                    role="admin"
                )
            ]
            
            # Add users to database
            for user in test_users:
                self.db.add(user)
            
            try:
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                raise e

    def get_by_username(self, username: str) -> User:
        """Get user by username."""
        if not self.db:
            return None
        return self.db.query(User).filter(User.username == username).first()

    def get_by_id(self, user_id: int) -> User:
        """Get user by ID."""
        if not self.db:
            return None
        return self.db.query(User).filter(User.id == user_id).first()

    def create(self, user: User) -> User:
        """Create a new user."""
        if not self.db:
            return None
        self.db.add(user)
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            self.db.rollback()
            raise e

    def update(self, user: User) -> User:
        """Update an existing user."""
        if not self.db:
            return None
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, user: User) -> bool:
        """Delete a user."""
        if not self.db:
            return False
        try:
            self.db.delete(user)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e