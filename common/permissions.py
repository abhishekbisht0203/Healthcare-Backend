from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Read access is granted to any authenticated user.
    Write access is restricted to the object's owner (or a staff member).
    """

    message = "You do not have permission to modify this resource."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        owner = getattr(obj, "created_by", None)
        if owner is None:
            return False

        return obj.created_by_id == request.user.id or request.user.is_staff


class IsAuthenticatedAndActive(permissions.BasePermission):
    """Only active, authenticated users are allowed through."""

    message = "Authentication with a valid active account is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)