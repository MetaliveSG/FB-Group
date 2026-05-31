"""Phase 0b — Order as a document with an external reference (POS integration seam)."""
from app.models.enums import OrderChannel
from app.services.orders import OrderItemInput, create_order
from app.tests.factories import make_world


def test_create_order_persists_external_reference_and_pos_channel(db):
    w = make_world(db)
    order = create_order(
        db,
        outlet_id=w.outlet_id,
        items=[OrderItemInput(menu_item_id=w.burger_id, quantity=1)],
        channel=OrderChannel.POS,
        source="pos:qashier",
        external_id="QASHIER-INV-0001",
    )
    assert order.channel == "pos"
    assert order.source == "pos:qashier"
    assert order.external_id == "QASHIER-INV-0001"


def test_native_order_leaves_external_reference_null(db):
    w = make_world(db)
    order = create_order(
        db,
        outlet_id=w.outlet_id,
        items=[OrderItemInput(menu_item_id=w.burger_id, quantity=1)],
    )
    assert order.source is None and order.external_id is None
    assert order.channel == "qr"
