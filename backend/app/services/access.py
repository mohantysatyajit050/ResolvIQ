from app.models.user import User, UserRole


def sees_everything(user: User) -> bool:
    """Agents and admins may see every order and ticket. Customers see only their own."""
    return user.role in (UserRole.AGENT.value, UserRole.ADMIN.value)
