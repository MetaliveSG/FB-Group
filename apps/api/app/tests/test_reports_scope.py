"""Report scope is RBAC-enforced (the SOURCE rule): a platform operator sees the whole ecosystem
("Platform", all merchants) + any node; a node account sees ITS node + downline only — never the
parent (upline), a sibling, or another tenant. Enforced server-side, not just hidden in the UI."""
from app.seed_breadtalk import build_breadtalk
from app.tests.factories import super_admin
from app.tests.helpers import H, staff_token


def _summary(client, tok, **q):
    qs = "&".join(f"{k}={v}" for k, v in q.items())
    return client.get(f"/api/v1/reports/summary?{qs}", headers=H(tok))


def test_operator_sees_platform_and_any_node(client, db):
    build_breadtalk(db)
    super_admin(db)
    t = staff_token(client, "root@platform.sg")
    assert _summary(client, t, platform="true").status_code == 200    # whole ecosystem
    assert _summary(client, t, node_id="btg").status_code == 200      # any node
    assert _summary(client, t, node_id="b_tb").status_code == 200
    assert _summary(client, t, node_id="b_dtf").status_code == 200    # the other tenant too


def test_node_account_downline_only(client, db):
    build_breadtalk(db)
    t = staff_token(client, "mgr.toastbox@breadtalk.sg")              # Manager @ b_tb (a sub-chain)
    assert _summary(client, t, node_id="b_tb").status_code == 200     # own node ✓
    assert _summary(client, t, node_id="btg").status_code == 403      # parent (upline) ✗
    assert _summary(client, t, node_id="b_dtf").status_code == 403    # sibling / other tenant ✗
    assert _summary(client, t, platform="true").status_code == 403    # not an operator ✗


def test_group_manager_sees_subtree_not_platform(client, db):
    build_breadtalk(db)
    t = staff_token(client, "ceo@breadtalk.sg")                       # Manager @ btg (top of group)
    assert _summary(client, t, node_id="btg").status_code == 200      # the whole group
    assert _summary(client, t, node_id="b_tb").status_code == 200     # a downline sub-chain ✓
    assert _summary(client, t, platform="true").status_code == 403    # still not an operator ✗
