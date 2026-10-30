"""Stable error codes for application boundaries."""

class DomainError(ValueError):
    code = "DOMAIN_ERROR"

class InvalidTransition(DomainError):
    code = "INVALID_TRANSITION"

class GuardRejected(DomainError):
    code = "GUARD_REJECTED"

class RevisionConflict(DomainError):
    code = "REVISION_CONFLICT"

class DependencyError(DomainError):
    code = "DEPENDENCY_INVALID"
