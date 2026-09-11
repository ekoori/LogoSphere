# permissions helpers - the single place that answers "may this user act for
# that entity".
import uuid
from conftest import RIVERSIDE, REPAIR_CAFE, TOOL_LIBRARY


def test_sphere_management_is_admin_only(api, app):
    from app.utils.permissions import can_manage_entity
    assert can_manage_entity(RIVERSIDE, api.uid('joe')) is True      # admin1
    assert can_manage_entity(RIVERSIDE, api.uid('marie')) is False   # participant only


def test_alliance_stewards_and_project_managers_manage(api, app):
    from app.utils.permissions import can_manage_entity
    assert can_manage_entity(REPAIR_CAFE, api.uid('marie')) is True   # steward
    assert can_manage_entity(TOOL_LIBRARY, api.uid('david')) is False  # not a contributor
    assert can_manage_entity(TOOL_LIBRARY, '16f033ca-2b2c-4745-a537-82999209774c') is True  # Steve, manager


def test_platform_admin_manages_anything(api, app):
    from app.utils.permissions import can_manage_entity, is_platform_admin
    joe = api.uid('joe')
    assert is_platform_admin(joe) is True
    assert is_platform_admin(api.uid('marie')) is False
    assert is_platform_admin(str(uuid.uuid4())) is False
    assert can_manage_entity(str(uuid.uuid4()), joe) is True


def test_bad_ids_never_raise(app):
    from app.utils.permissions import can_manage_entity, is_platform_admin, entity_sphere_ids
    assert can_manage_entity('not-a-uuid', 'nope') is False
    assert is_platform_admin(None) is False
    assert entity_sphere_ids('garbage') == set()
