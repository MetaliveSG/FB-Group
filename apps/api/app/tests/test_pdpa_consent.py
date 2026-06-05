"""PDPA consent at capture: a new diner must accept the privacy notice; marketing is express opt-in
(default off); every consent action is recorded in the audit trail; consent is withdrawable."""
from sqlalchemy import select

from app.models.identity import Customer, CustomerConsent
from app.services.consent import CONSENT_VERSION
from app.tests.helpers import H


def _otp(client, phone, **extra):
    code = client.post("/api/v1/auth/customer/otp/request", json={"phone": phone}).json()["debug_code"]
    return client.post("/api/v1/auth/customer/otp/verify", json={"phone": phone, "code": code, **extra})


def test_new_customer_blocked_without_terms(client, db):
    r = _otp(client, "+6590000001")  # no accepted_terms
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "consent_required"
    assert db.scalar(select(Customer).where(Customer.phone == "+6590000001")) is None  # not created


def test_signup_records_consent_and_marketing_defaults_off(client, db):
    r = _otp(client, "+6590000002", accepted_terms=True)  # marketing omitted → opt-in off
    assert r.status_code == 200
    cust = db.scalar(select(Customer).where(Customer.phone == "+6590000002"))
    assert cust.marketing_consent is False
    rows = db.scalars(select(CustomerConsent).where(CustomerConsent.customer_id == cust.id)).all()
    by_purpose = {c.purpose: c for c in rows}
    assert by_purpose["terms"].granted is True
    assert by_purpose["marketing"].granted is False
    assert by_purpose["terms"].version == CONSENT_VERSION
    assert by_purpose["terms"].source == "qr_signup"


def test_signup_with_marketing_opt_in(client, db):
    r = _otp(client, "+6590000003", accepted_terms=True, marketing_opt_in=True,
             consent_merchant_id="m_demo")
    assert r.status_code == 200
    assert r.json()["customer"]["marketing_consent"] is True
    cust = db.scalar(select(Customer).where(Customer.phone == "+6590000003"))
    mk = db.scalar(select(CustomerConsent).where(CustomerConsent.customer_id == cust.id,
                                                 CustomerConsent.purpose == "marketing"))
    assert mk.granted is True and mk.merchant_id == "m_demo"


def test_returning_customer_not_reprompted(client, db):
    assert _otp(client, "+6590000004", accepted_terms=True, marketing_opt_in=True).status_code == 200
    cust = db.scalar(select(Customer).where(Customer.phone == "+6590000004"))
    cid = cust.id
    # second login without accepted_terms must still succeed (consent already on file) + not flip marketing
    r2 = _otp(client, "+6590000004")
    assert r2.status_code == 200
    db.expire_all()
    cust = db.get(Customer, cid)
    assert cust.marketing_consent is True
    terms = db.scalars(select(CustomerConsent).where(CustomerConsent.customer_id == cid,
                                                     CustomerConsent.purpose == "terms")).all()
    assert len(terms) == 1  # captured once, at signup — not on every login


def test_withdraw_marketing_consent(client, db):
    tok = _otp(client, "+6590000005", accepted_terms=True, marketing_opt_in=True).json()["access_token"]
    # withdraw
    r = client.post("/api/v1/auth/customer/consent", json={"marketing_opt_in": False}, headers=H(tok))
    assert r.status_code == 200 and r.json()["marketing_consent"] is False
    cust = db.scalar(select(Customer).where(Customer.phone == "+6590000005"))
    events = db.scalars(select(CustomerConsent).where(CustomerConsent.customer_id == cust.id,
                                                      CustomerConsent.purpose == "marketing")
                        .order_by(CustomerConsent.created_at)).all()
    assert [e.granted for e in events] == [True, False]   # grant at signup, then withdrawal
    assert events[-1].source == "profile"


def test_consent_endpoint_requires_customer_token(client, db):
    assert client.post("/api/v1/auth/customer/consent", json={"marketing_opt_in": True}).status_code in (401, 403)
