import os
os.environ["DATABASE_URL"] = "sqlite:////tmp/bt_demo.db"
if os.path.exists("/tmp/bt_demo.db"): os.remove("/tmp/bt_demo.db")
from sqlalchemy import select
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.seed_breadtalk import build_breadtalk, NODES
from app.services import org_tree
from app.auth.access import resolve_scope, ALL_OUTLETS
from app.models.org import OrgNode
from app.models.identity import User

Base.metadata.create_all(engine)
label = {n[0]: n[3] for n in NODES}
with SessionLocal() as db:
    res = build_breadtalk(db)
    print(f"=== BreadTalk member-tree: {res['nodes']} nodes, depth 0..{res['max_depth']}, {res['merchants']} merchants, {res['accounts']} accounts ===\n")
    for n in db.scalars(select(OrgNode).order_by(OrgNode.path)).all():
        flag = " [Storefront]" if n.sells else (" [Loyalty+Settlement boundary]" if n.is_loyalty_domain else "")
        print("   " * n.depth + f"{label.get(n.id,n.id)}  <{n.role}>{flag}")
    print("\n=== Each account's effective reach (authority cascades DOWN its node's subtree) ===")
    for email in ["ceo@breadtalk.sg","coo@breadtalk.sg","cfo@breadtalk.sg",
                  "bm.toastbox@breadtalk.sg","am.foodrepublic@breadtalk.sg",
                  "om.ion@breadtalk.sg","stall.chicken@breadtalk.sg","bm.dtf@breadtalk.sg"]:
        u = db.scalar(select(User).where(User.email==email)); s = resolve_scope(db, u)
        parts=[]
        for mid in sorted(s.accessible_merchant_ids):
            ol = s.outlet_limit(mid)
            outs = "ALL outlets" if ol is ALL_OUTLETS else ", ".join(sorted(label.get(o,o) for o in ol))
            parts.append(f"{label.get(mid,mid)} → {outs}")
        print(f"  {email:32} {' | '.join(parts)}")
