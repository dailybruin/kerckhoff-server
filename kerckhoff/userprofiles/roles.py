from rolepermissions.roles import AbstractUserRole


class KerckhoffUserRole(AbstractUserRole):
    ABBRV: str


class Contributor(KerckhoffUserRole):
    ABBRV = "CT"
    available_permissions = set()


class Editor(AbstractUserRole):
    ABBRV = "ED"
    available_permissions = Contributor.available_permissions | set()


class Admin(AbstractUserRole):
    ABBRV = "AD"
    available_permissions = Editor.available_permissions | set()


all_roles = [Contributor, Editor, Admin]
