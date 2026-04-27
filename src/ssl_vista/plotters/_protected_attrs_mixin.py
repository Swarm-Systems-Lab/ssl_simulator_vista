"""
Mixin class to protect attributes from direct reassignment by child classes.

This mixin provides a __setattr__ override that warns when protected attributes
are directly reassigned, helping enforce the pattern of modifying container contents
rather than replacing entire containers.
"""

__all__ = ["ProtectedAttrsMixin"]


class ProtectedAttrsMixin:
    """
    Mixin class that protects specified attributes from direct reassignment.

    Child classes should define a class-level `_PROTECTED_ATTRS` frozenset
    containing attribute names that should not be directly reassigned.

    Example:
        class MyClass(ProtectedAttrsMixin):
            _PROTECTED_ATTRS = frozenset(['data', 'config', 'cache'])

            def __init__(self):
                super().__init__()
                self.data = {}
                self.config = {}

    Usage:
        obj.data['key'] = value  # OK - modifying items
        obj.data = {}            # WARNING - direct reassignment
    """

    _PROTECTED_ATTRS = frozenset()  # Override in child class

    def __init__(self, *args, **kwargs):
        """Initialize with protection disabled during setup."""
        super().__init__(*args, **kwargs)

    def __setattr__(self, name, value):
        """
        Intercept attribute assignments to protect managed attributes.
        Issues a warning when child classes try to directly reassign protected attributes.
        """
        # # Allow all assignments during initialization
        # if hasattr(self, '_initializing') and self._initializing:
        #     object.__setattr__(self, name, value)
        #     return

        # Check if this is a protected attribute being reassigned (not first assignment)
        if name in self._PROTECTED_ATTRS and hasattr(self, name):
            class_name = self.__class__.__name__
            raise RuntimeError(
                f"Direct reassignment to 'self.{name}' detected in {class_name}! "
                f"This attribute is managed by the base class. "
                f"Modify individual items instead: self.{name}[key] = value or self.{name}.method()"
            )

        object.__setattr__(self, name, value)
