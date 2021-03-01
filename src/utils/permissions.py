from functools import wraps

from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.users import UserModel, UserRole
from src.utils.api_response import APIResponse


def admin_required(fn):
  @wraps(fn)
  def wrapper(*args, **kwargs):
    session_user = UserModel.get_first([
      UserModel.email == get_jwt_identity()
    ])
    if session_user.role != UserRole.ADMIN:
      return APIResponse.error_403("Permission denied!")

    return fn(*args, **kwargs)

  return wrapper
