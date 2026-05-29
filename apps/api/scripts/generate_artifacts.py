"""Reset+seed the demo DB and emit proof artifacts into /artifacts.

Run: python -m scripts.generate_artifacts
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.db.session import engine
from app.main import app
from app.seed import CUSTOMER_PASSWORD, DEMO_PASSWORD, reset_and_seed

ART = Path(__file__).resolve().parents[3] / "artifacts"  # repo-root/artifacts
ART.mkdir(exist_ok=True)


def _write(name: str, data) -> None:
    path = ART / name
    if name.endswith(".json"):
        path.write_text(json.dumps(data, indent=2, default=str))
    else:
        path.write_text(str(data))
    print(f"  wrote {path.relative_to(ART.parent)}")


def main() -> None:
    summary = reset_and_seed()
    client = TestClient(app)

    # OpenAPI spec
    _write("openapi.json", app.openapi())

    # DB schema (table list)
    tables = sorted(inspect(engine).get_table_names())
    _write("schema_tables.txt", f"{len(tables)} tables:\n" + "\n".join(f" - {t}" for t in tables))

    # Login as Makan owner
    tok = client.post("/api/v1/auth/staff/login",
                      json={"email": "owner@makan.sg", "password": DEMO_PASSWORD}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}

    customers = client.get("/api/v1/crm/customers", headers=H).json()
    _write("crm_customers_sample.json", customers[:10])
    _write("segment_summary.json", client.get("/api/v1/crm/segments", headers=H).json())
    _write("sales_summary.json", client.get("/api/v1/reports/summary", headers=H).json())
    _write("forecast_sample.json", client.get("/api/v1/reports/forecast?horizon=7", headers=H).json())
    _write("top_items.json", client.get("/api/v1/reports/top-items", headers=H).json())
    _write("outlet_comparison.json", client.get("/api/v1/reports/outlets", headers=H).json())

    # A sample full customer profile
    if customers:
        cid = customers[0]["id"]
        prof = client.get(f"/api/v1/crm/customers/{cid}", headers=H).json()
        _write("customer_profile_sample.json", prof)

    creds = f"""# Demo Credentials

Seed summary: {json.dumps(summary, indent=2)}

## Staff / back-office (password: {DEMO_PASSWORD})
| Role           | Email                       | Scope                |
|----------------|-----------------------------|----------------------|
| Super Admin    | superadmin@platform.sg      | Platform (all)       |
| Merchant Owner | owner@makan.sg              | Makan Express        |
| Outlet Manager | manager.orchard@makan.sg    | Orchard outlet only  |
| Staff/Cashier  | staff.orchard@makan.sg      | Orchard outlet only  |
| Merchant Owner | owner@kopiculture.sg        | Kopi Culture         |

## Customers (password: {CUSTOMER_PASSWORD}; or OTP via mock)
- Emails cust0@example.sg .. cust24@example.sg
- Sample QR token (Orchard table 1): {summary['sample_qr_token']}
"""
    _write("demo_credentials.md", creds)
    print("\nArtifacts generated.")


if __name__ == "__main__":
    main()
