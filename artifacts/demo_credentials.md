# Demo Credentials

Seed summary: {
  "merchants": [
    "Makan Express",
    "Kopi Culture",
    "Hawker Hub"
  ],
  "merchant1_id": "ba4f4eb5716c4f10a9672987ff4feeeb",
  "merchant2_id": "8732e1c5b9ea419780d4bbdc9e555623",
  "merchant3_id": "8b4ccfc8dcc84c51b6c7ba833e020363",
  "outlet_orchard_id": "fce3cdfc0b7d48afab76e2df808c8fac",
  "outlet_tampines_id": "557ea486916e4c3db1b0dc23d36f0a60",
  "coalition": "SG Eats Rewards",
  "customers": 40,
  "opportunities": 8,
  "activities": 8,
  "sample_qr_token": "orchard-01"
}

## Staff / back-office (password: Password123!)
| Role           | Email                       | Scope                |
|----------------|-----------------------------|----------------------|
| Super Admin    | superadmin@platform.sg      | Platform (all)       |
| Merchant Owner | owner@makan.sg              | Makan Express        |
| Outlet Manager | manager.orchard@makan.sg    | Orchard outlet only  |
| Staff/Cashier  | staff.orchard@makan.sg      | Orchard outlet only  |
| Merchant Owner | owner@kopiculture.sg        | Kopi Culture         |

## Customers (password: Customer123!; or OTP via mock)
- Emails cust0@example.sg .. cust24@example.sg
- Sample QR token (Orchard table 1): orchard-01

## Bedok Food Hall (foodcourt)
- Merchant owner: `owner@bedokfoodhall.sg` / `Password123!` (operator can also drill in via /operator)
- Customer QR: `http://localhost:3001/t/foodhall-01` (foodcourt → 3 stalls)
