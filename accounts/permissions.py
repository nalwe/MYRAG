def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.profile.role == "admin"
    )

def is_premium(user):
    return user.is_authenticated and user.profile.role == "premium"

def is_basic(user):
    return user.is_authenticated and user.profile.role == "basic"
