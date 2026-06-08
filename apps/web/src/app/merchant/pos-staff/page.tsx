"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiBase } from "@/lib/api";
import { getStaffToken, getOperatorMerchant } from "@/lib/auth";
import MerchantSidebar from "@/components/MerchantSidebar";
import PosStaffCard from "@/components/PosStaffCard";

// POS module — Staff & PINs (POS operators: Supervisor / Cashier, PIN-only). Moved out of Settings
// into its own page under the "Point of Sale" nav section so it shows/hides with the POS module toggle.
export default function PosStaffPage() {
  const router = useRouter();
  useEffect(() => {
    if (!getStaffToken()) router.push("/merchant/login");
  }, [router]);

  return (
    <MerchantSidebar active="pos_staff">
      <div className="page-header">
        <h1 className="page-title">Point of Sale</h1>
        <p className="page-subtitle">Staff &amp; PINs — POS operators (Supervisor / Cashier), PIN-only at the till</p>
      </div>
      <PosStaffCard base={getApiBase()} merchantId={getOperatorMerchant()?.id} />
    </MerchantSidebar>
  );
}
