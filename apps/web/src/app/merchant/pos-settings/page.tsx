"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiBase } from "@/lib/api";
import { getStaffToken, getOperatorMerchant } from "@/lib/auth";
import MerchantSidebar from "@/components/MerchantSidebar";
import PosReceiptCard from "@/components/PosReceiptCard";

// POS module → "POS Settings": point-of-sale configuration (receipt header now; day-end/drawer later).
// Separate from the merchant-wide "Settings" (Admin) to avoid a duplicate label.
export default function PosSettingsPage() {
  const router = useRouter();
  useEffect(() => {
    if (!getStaffToken()) router.push("/merchant/login");
  }, [router]);

  return (
    <MerchantSidebar active="pos_settings">
      <div className="page-header">
        <h1 className="page-title">POS Settings</h1>
        <p className="page-subtitle">Point-of-sale configuration — the receipt header printed at the till</p>
      </div>
      <PosReceiptCard base={getApiBase()} merchantId={getOperatorMerchant()?.id} />
    </MerchantSidebar>
  );
}
