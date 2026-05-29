"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  crmMyTasks,
  crmCustomers,
  crmCustomerTasks,
  crmUpdateTask,
} from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import { getApiBase } from "@/lib/api";
import { formatDate } from "@/lib/format";
import MerchantSidebar from "@/components/MerchantSidebar";
import type { TaskOut } from "@fbgroup/api-client";

const PRIORITY_COLOR: Record<string, { bg: string; fg: string }> = {
  high: { bg: "#fef2f2", fg: "#991b1b" },
  normal: { bg: "#eff6ff", fg: "#1e40af" },
  low: { bg: "#f3f4f6", fg: "#374151" },
};

interface CustomerRef {
  id: string;
  name: string;
}

export default function MyTasksPage() {
  const router = useRouter();
  const base = getApiBase();

  const [tasks, setTasks] = useState<TaskOut[]>([]);
  // Map task id -> customer (built by cross-referencing customer task lists,
  // since TaskOut does not expose customer_id directly).
  const [taskCustomer, setTaskCustomer] = useState<Record<string, CustomerRef>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const load = useCallback(
    async (tok: string) => {
      const mid = getOperatorMerchant()?.id;
      const myTasks = await crmMyTasks(base, tok, mid);
      setTasks(myTasks);

      // Build task -> customer map using customers that have open tasks.
      try {
        const customers = await crmCustomers(base, tok, undefined, mid);
        const withTasks = customers.filter((c) => c.open_tasks > 0);
        const map: Record<string, CustomerRef> = {};
        await Promise.all(
          withTasks.map(async (c) => {
            const ctasks = await crmCustomerTasks(base, tok, c.id, mid).catch(
              () => [] as TaskOut[]
            );
            for (const t of ctasks) {
              map[t.id] = { id: c.id, name: c.full_name ?? "Customer" };
            }
          })
        );
        setTaskCustomer(map);
      } catch {
        // Non-fatal: still show tasks without customer linking.
      }
    },
    [base]
  );

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    setLoading(true);
    load(tok)
      .then(() => setLoading(false))
      .catch((err) => {
        if (err.message?.includes("401")) {
          clearStaffToken();
          router.push("/merchant/login");
        } else {
          setError(err.message ?? "Failed to load tasks");
          setLoading(false);
        }
      });
  }, [load, router]);

  async function completeTask(task: TaskOut) {
    const tok = getStaffToken();
    if (!tok) return;
    setUpdatingId(task.id);
    try {
      await crmUpdateTask(base, tok, task.id, "done", getOperatorMerchant()?.id);
      // Drop from the open-tasks list.
      setTasks((prev) => prev.filter((t) => t.id !== task.id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to complete task");
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <MerchantSidebar active="tasks">
      <div className="page-header">
        <h1 className="page-title">My Tasks</h1>
        <p className="page-subtitle">Your open follow-up tasks across customers</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="page-loading">
          <div className="spinner" /> Loading tasks…
        </div>
      ) : tasks.length === 0 ? (
        <div className="card text-center" style={{ padding: 40 }}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>🎉</div>
          <div style={{ fontWeight: 700, fontSize: 18 }}>All caught up!</div>
          <p className="text-muted">You have no open tasks.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          {tasks.map((task, i) => {
            const pc = PRIORITY_COLOR[task.priority] ?? PRIORITY_COLOR.normal;
            const cust = taskCustomer[task.id];
            return (
              <div
                key={task.id}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  padding: "14px 20px",
                  borderBottom: i < tasks.length - 1 ? "1px solid var(--color-border)" : "none",
                }}
              >
                <input
                  type="checkbox"
                  checked={false}
                  disabled={updatingId === task.id}
                  onChange={() => completeTask(task)}
                  style={{ width: "auto", marginTop: 4, cursor: "pointer" }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{task.title}</div>
                  {task.description && (
                    <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                      {task.description}
                    </div>
                  )}
                  <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 6, flexWrap: "wrap" }}>
                    <span className="badge" style={{ background: pc.bg, color: pc.fg, fontSize: 11 }}>
                      {task.priority}
                    </span>
                    {task.due_date && (
                      <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                        Due {formatDate(task.due_date)}
                      </span>
                    )}
                    {cust && (
                      <a
                        href={`/merchant/crm/${cust.id}`}
                        style={{ fontSize: 13, fontWeight: 600 }}
                      >
                        {cust.name} →
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </MerchantSidebar>
  );
}
