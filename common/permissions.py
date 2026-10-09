from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Requires an authenticated account for every request.

    Read access is granted to any authenticated user.
    Write access is restricted to the object's owner (or a staff member).
    """

    message = "You do not have permission to modify this resource."

    def has_permission(self, request, view):
        # Without this guard an anonymous request would reach get_queryset()
        # and be filtered by AnonymousUser instead of being rejected with 401.
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        owner = getattr(obj, "created_by", None)
        if owner is None:
            return False

        return obj.created_by_id == request.user.id or request.user.is_staff


class IsMappingParticipantOrReadOnly(permissions.BasePermission):
    """
    Write access to an assignment is limited to the users involved in it.

    A user participates in an assignment when they created the patient, created
    the doctor, or performed the assignment. Staff may always write.
    """

    message = "You do not have permission to modify this assignment."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        if user.is_staff:
            return True

        return (
            obj.patient.created_by_id == user.id
            or obj.doctor.created_by_id == user.id
            or obj.assigned_by_id == user.id
        )


class IsAuthenticatedAndActive(permissions.BasePermission):
    """Only active, authenticated users are allowed through."""

    message = "Authentication with a valid active account is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)