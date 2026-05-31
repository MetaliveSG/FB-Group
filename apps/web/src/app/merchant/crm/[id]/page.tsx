"use client";

import { useState, useEffect, useCallback, Fragment } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  crmCustomerProfile,
  addTag,
  addNote,
  crmTimeline,
  crmCreateTask,
  crmUpdateTask,
  crmAssignOwner,
  customerOpportunities,
  createOpportunity,
  logActivity,
} from "@/lib/api";
import {
  getStaffToken,
  clearStaffToken,
  getStaffUser,
  getOperatorMerchant,
} from "@/lib/auth";
import { getApiBase } from "@/lib/api";
import { formatSGD, churnColor, formatDate, relativeTime } from "@/lib/format";
import MerchantSidebar from "@/components/MerchantSidebar";
import {
  OPPORTUNITY_STAGES,
  type CustomerProfile,
  type TimelineEvent,
  type TaskOut,
  type TaskPriority,
  type Opportunity,
  type OpportunityStage,
  type ActivityType,
} from "@fbgroup/api-client";

const OPP_STAGE_COLOR: Record<string, { bg: string; fg: string }> = {
  prospecting: { bg: "#eff6ff", fg: "#1e40af" },
  qualified: { bg: "#eef2ff", fg: "#4338ca" },
  proposal: { bg: "#fef9c3", fg: "#854d0e" },
  negotiation: { bg: "#ffedd5", fg: "#9a3412" },
  won: { bg: "#dcfce7", fg: "#166534" },
  lost: { bg: "#e5e7eb", fg: "#4b5563" },
};

const ACTIVITY_TYPES: ActivityType[] = ["call", "email", "meeting", "whatsapp", "note"];

function SidebarLayout({ children }: { children: React.ReactNode }) {
  return <MerchantSidebar active="crm">{children}</MerchantSidebar>;
}

const TIMELINE_ICON: Record<string, { icon: string; color: string }> = {
  order: { icon: "🛒", color: "#1b6ca8" },
  payment: { icon: "💳", color: "#16a34a" },
  reward_earn: { icon: "⭐", color: "#d97706" },
  reward_redeem: { icon: "🎁", color: "#9333ea" },
  note: { icon: "📝", color: "#6b7280" },
  task: { icon: "📌", color: "#dc2626" },
  task_done: { icon: "✅", color: "#16a34a" },
  activity_call: { icon: "📞", color: "#0ea5e9" },
  activity_email: { icon: "✉️", color: "#6366f1" },
  activity_meeting: { icon: "🤝", color: "#0d9488" },
  activity_whatsapp: { icon: "💬", color: "#22c55e" },
  activity_note: { icon: "🗒️", color: "#6b7280" },
};

const PRIORITY_COLOR: Record<string, { bg: string; fg: string }> = {
  high: { bg: "#fef2f2", fg: "#991b1b" },
  normal: { bg: "#eff6ff", fg: "#1e40af" },
  low: { bg: "#f3f4f6", fg: "#374151" },
};

export default function CustomerProfilePage() {
  const router = useRouter();
  const params = useParams();
  const customerId = params.id as string;
  const base = getApiBase();

  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTag, setNewTag] = useState("");
  const [newNote, setNewNote] = useState("");
  const [addingTag, setAddingTag] = useState(false);
  const [addingNote, setAddingNote] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [expandedOrderId, setExpandedOrderId] = useState<string | null>(null);  // order detail drill-down

  // Task form
  const [taskTitle, setTaskTitle] = useState("");
  const [taskPriority, setTaskPriority] = useState<TaskPriority>("normal");
  const [taskDue, setTaskDue] = useState("");
  const [addingTask, setAddingTask] = useState(false);
  const [updatingTaskId, setUpdatingTaskId] = useState<string | null>(null);

  // Owner
  const [savingOwner, setSavingOwner] = useState(false);
  const staffUser = typeof window !== "undefined" ? getStaffUser() : null;

  // Opportunities
  const [opps, setOpps] = useState<Opportunity[]>([]);
  const [oppName, setOppName] = useState("");
  const [oppAmount, setOppAmount] = useState("");
  const [oppStage, setOppStage] = useState<OpportunityStage>("prospecting");
  const [oppClose, setOppClose] = useState("");
  const [addingOpp, setAddingOpp] = useState(false);

  // Activity logging
  const [actType, setActType] = useState<ActivityType>("call");
  const [actSubject, setActSubject] = useState("");
  const [actBody, setActBody] = useState("");
  const [loggingAct, setLoggingAct] = useState(false);

  const reloadProfile = useCallback(
    async (tok: string) => {
      const mid = getOperatorMerchant()?.id;
      const [data, tl, op] = await Promise.all([
        crmCustomerProfile(base, tok, customerId, mid),
        crmTimeline(base, tok, customerId, mid).catch(() => [] as TimelineEvent[]),
        customerOpportunities(base, tok, customerId, mid).catch(() => [] as Opportunity[]),
      ]);
      setProfile(data);
      setTimeline(tl);
      setOpps(op);
    },
    [base, customerId]
  );

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    setLoading(true);
    reloadProfile(tok)
      .then(() => setLoading(false))
      .catch((err) => {
        if (err.message?.includes("401")) {
          clearStaffToken();
          router.push("/merchant/login");
        } else {
          setError(err.message ?? "Failed to load profile");
          setLoading(false);
        }
      });
  }, [reloadProfile, router]);

  function flashMsg(msg: string) {
    setActionMsg(msg);
    setTimeout(() => setActionMsg(null), 2500);
  }

  async function handleAddTask(e: React.FormEvent) {
    e.preventDefault();
    if (!taskTitle.trim()) return;
    const tok = getStaffToken();
    if (!tok) return;
    setAddingTask(true);
    try {
      await crmCreateTask(
        base,
        tok,
        customerId,
        {
          title: taskTitle.trim(),
          priority: taskPriority,
          due_date: taskDue || undefined,
        },
        getOperatorMerchant()?.id
      );
      setTaskTitle("");
      setTaskDue("");
      setTaskPriority("normal");
      await reloadProfile(tok);
      flashMsg("Task created!");
    } catch (err: unknown) {
      flashMsg(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setAddingTask(false);
    }
  }

  async function handleToggleTask(task: TaskOut) {
    const tok = getStaffToken();
    if (!tok) return;
    setUpdatingTaskId(task.id);
    try {
      await crmUpdateTask(
        base,
        tok,
        task.id,
        task.status === "done" ? "open" : "done",
        getOperatorMerchant()?.id
      );
      await reloadProfile(tok);
    } catch (err: unknown) {
      flashMsg(err instanceof Error ? err.message : "Failed to update task");
    } finally {
      setUpdatingTaskId(null);
    }
  }

  async function handleSetOwner(ownerUserId: string | null) {
    const tok = getStaffToken();
    if (!tok) return;
    setSavingOwner(true);
    try {
      await crmAssignOwner(base, tok, customerId, ownerUserId, getOperatorMerchant()?.id);
      await reloadProfile(tok);
      flashMsg(ownerUserId ? "Owner assigned!" : "Owner cleared!");
    } catch (err: unknown) {
      flashMsg(err instanceof Error ? err.message : "Failed to update owner");
    } finally {
      setSavingOwner(false);
    }
  }

  async function handleAddOpp(e: React.FormEvent) {
    e.preventDefault();
    if (!oppName.trim()) return;
    const tok = getStaffToken();
    if (!tok) return;
    setAddingOpp(true);
    try {
      await createOpportunity(
        base,
        tok,
        customerId,
        {
          name: oppName.trim(),
          amount: parseFloat(oppAmount) || 0,
          stage: oppStage,
          expected_close_date: oppClose || undefined,
        },
        getOperatorMerchant()?.id
      );
      setOppName("");
      setOppAmount("");
      setOppStage("prospecting");
      setOppClose("");
      await reloadProfile(tok);
      flashMsg("Opportunity created!");
    } catch (err: unknown) {
      flashMsg(err instanceof Error ? err.message : "Failed to create opportunity");
    } finally {
      setAddingOpp(false);
    }
  }

  async function handleLogActivity(e: React.FormEvent) {
    e.preventDefault();
    if (!actSubject.trim()) return;
    const tok = getStaffToken();
    if (!tok) return;
    setLoggingAct(true);
    try {
      await logActivity(
        base,
        tok,
        customerId,
        {
          activity_type: actType,
          subject: actSubject.trim(),
          body: actBody.trim() || undefined,
        },
        getOperatorMerchant()?.id
      );
      setActSubject("");
      setActBody("");
      await reloadProfile(tok);
      flashMsg("Activity logged!");
    } catch (err: unknown) {
      flashMsg(err instanceof Error ? err.message : "Failed to log activity");
    } finally {
      setLoggingAct(false);
    }
  }

  async function handleAddTag(e: React.FormEvent) {
    e.preventDefault();
    if (!newTag.trim()) return;
    const tok = getStaffToken();
    if (!tok) return;
    setAddingTag(true);
    try {
      await addTag(base, tok, customerId, newTag.trim());
      setProfile((prev) =>
        prev ? { ...prev, tags: [...prev.tags, newTag.trim()] } : prev
      );
      setNewTag("");
      setActionMsg("Tag added!");
      setTimeout(() => setActionMsg(null), 2000);
    } catch (err: unknown) {
      setActionMsg(err instanceof Error ? err.message : "Failed to add tag");
    } finally {
      setAddingTag(false);
    }
  }

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!newNote.trim()) return;
    const tok = getStaffToken();
    if (!tok) return;
    setAddingNote(true);
    try {
      await addNote(base, tok, customerId, newNote.trim());
      setProfile((prev) =>
        prev
          ? {
              ...prev,
              notes: [
                {
                  id: `temp-${Date.now()}`,
                  body: newNote.trim(),
                  created_at: new Date().toISOString(),
                },
                ...prev.notes,
              ],
            }
          : prev
      );
      setNewNote("");
      setActionMsg("Note saved!");
      setTimeout(() => setActionMsg(null), 2000);
    } catch (err: unknown) {
      setActionMsg(err instanceof Error ? err.message : "Failed to add note");
    } finally {
      setAddingNote(false);
    }
  }

  if (loading) {
    return (
      <SidebarLayout>
        <div className="page-loading">
          <div className="spinner" /> Loading customer profile…
        </div>
      </SidebarLayout>
    );
  }

  if (error || !profile) {
    return (
      <SidebarLayout>
        <div className="alert alert-error">{error ?? "Profile not found"}</div>
        <a href="/merchant/crm" className="btn btn-secondary">
          ← Back to CRM
        </a>
      </SidebarLayout>
    );
  }

  const { customer, metrics } = profile;
  const initials = (customer.full_name ?? "?")
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <SidebarLayout>
      {/* Back */}
      <a
        href="/merchant/crm"
        style={{ fontSize: 14, color: "var(--color-text-muted)", display: "inline-flex", alignItems: "center", gap: 4, marginBottom: 20 }}
      >
        ← All Customers
      </a>

      {/* Profile header */}
      <div
        className="profile-header"
        style={{ justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div className="profile-avatar">{initials}</div>
          <div>
            <div className="profile-name">{customer.full_name ?? "Unknown"}</div>
            <div className="profile-meta">
              {customer.email && <span>{customer.email}</span>}
              {customer.email && customer.phone && " · "}
              {customer.phone && <span>{customer.phone}</span>}
              {customer.birthday && <span> · Born {formatDate(customer.birthday)}</span>}
            </div>
          </div>
        </div>

        {/* Owner control */}
        <div
          style={{
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius)",
            padding: "10px 14px",
            background: "var(--color-surface)",
            minWidth: 220,
          }}
        >
          <div className="kpi-label" style={{ marginBottom: 6 }}>
            Account Owner
          </div>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>
            {profile.owner_name ?? (
              <span style={{ color: "var(--color-text-muted)", fontWeight: 400 }}>Unassigned</span>
            )}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {profile.owner_user_id !== staffUser?.id && staffUser && (
              <button
                className="btn btn-secondary btn-sm"
                disabled={savingOwner}
                onClick={() => handleSetOwner(staffUser.id)}
              >
                Assign to me
              </button>
            )}
            {profile.owner_user_id && (
              <button
                className="btn btn-secondary btn-sm"
                disabled={savingOwner}
                onClick={() => handleSetOwner(null)}
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {actionMsg && <div className="alert alert-success">{actionMsg}</div>}

      {/* Metric cards */}
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        <div className="kpi-card">
          <div className="kpi-label">Total Spend</div>
          <div className="kpi-value">{formatSGD(metrics.total_spend)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Avg. Order</div>
          <div className="kpi-value">{formatSGD(metrics.avg_spend)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Visits</div>
          <div className="kpi-value">{metrics.visit_count}</div>
          <div className="kpi-sub">{metrics.visits_per_month.toFixed(1)}/month</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Coins Balance</div>
          <div className="kpi-value">{metrics.points_balance.toLocaleString()}</div>
          <div className="kpi-sub">Lifetime: {metrics.lifetime_points.toLocaleString()}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Tier</div>
          <div
            className="kpi-value"
            style={{
              color:
                metrics.tier === "gold"
                  ? "#d97706"
                  : metrics.tier === "silver"
                  ? "#6b7280"
                  : "#b45309",
            }}
          >
            {metrics.tier.charAt(0).toUpperCase() + metrics.tier.slice(1)}
          </div>
          <div className="kpi-sub">{metrics.lifecycle_stage.replace(/_/g, " ")}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Churn Risk</div>
          <div className="kpi-value" style={{ color: churnColor(metrics.churn_label) }}>
            {(metrics.churn_risk * 100).toFixed(0)}%
          </div>
          <div className="kpi-sub" style={{ color: churnColor(metrics.churn_label) }}>
            {metrics.churn_label}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">First Visit</div>
          <div className="kpi-value" style={{ fontSize: 16 }}>
            {formatDate(metrics.first_visit_at)}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Last Visit</div>
          <div className="kpi-value" style={{ fontSize: 16 }}>
            {formatDate(metrics.last_visit_at)}
          </div>
          {metrics.days_since_last_visit != null && (
            <div className="kpi-sub">{metrics.days_since_last_visit} days ago</div>
          )}
        </div>
      </div>

      {/* Segments & Tags */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="card-title" style={{ marginBottom: 12 }}>
            Segments
          </div>
          <div className="tag-list">
            {metrics.segments.length === 0 ? (
              <span style={{ color: "var(--color-text-muted)", fontSize: 14 }}>None</span>
            ) : (
              metrics.segments.map((seg) => (
                <span key={seg} className="tag" style={{ background: "#e0e7ff", color: "#3730a3" }}>
                  {seg}
                </span>
              ))
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-title" style={{ marginBottom: 12 }}>
            Tags
          </div>
          <div className="tag-list">
            {profile.tags.length === 0 ? (
              <span style={{ color: "var(--color-text-muted)", fontSize: 14 }}>No tags yet</span>
            ) : (
              profile.tags.map((tag, i) => (
                <span key={i} className="tag">
                  {tag}
                </span>
              ))
            )}
          </div>
          <form onSubmit={handleAddTag} className="inline-form">
            <input
              type="text"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              placeholder="Add tag…"
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={addingTag}>
              {addingTag ? "…" : "Add"}
            </button>
          </form>
        </div>
      </div>

      {/* Notes */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title" style={{ marginBottom: 12 }}>
          Notes
        </div>
        <form onSubmit={handleAddNote} className="inline-form" style={{ marginBottom: 16 }}>
          <input
            type="text"
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            placeholder="Add a note about this customer…"
          />
          <button type="submit" className="btn btn-primary btn-sm" disabled={addingNote}>
            {addingNote ? "…" : "Save"}
          </button>
        </form>
        {profile.notes.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)", fontSize: 14 }}>No notes yet.</p>
        ) : (
          profile.notes.map((note) => (
            <div
              key={note.id}
              style={{
                padding: "10px 0",
                borderBottom: "1px solid var(--color-border)",
                fontSize: 14,
              }}
            >
              <div>{note.body}</div>
              <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>
                {formatDate(note.created_at)}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Opportunities + Log Activity */}
      <div className="grid-2" style={{ marginBottom: 24, alignItems: "start" }}>
        {/* Opportunities */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: 12 }}>
            Opportunities
          </div>

          {opps.length === 0 ? (
            <p style={{ color: "var(--color-text-muted)", fontSize: 13, marginTop: 0 }}>
              No opportunities yet.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
              {opps.map((o) => {
                const c = OPP_STAGE_COLOR[o.stage] ?? OPP_STAGE_COLOR.prospecting;
                return (
                  <div
                    key={o.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 8,
                      border: "1px solid var(--color-border, #e5e7eb)",
                      borderRadius: 8,
                      padding: "8px 10px",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{o.name}</div>
                      <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                        {formatSGD(o.amount)}
                        {o.expected_close_date ? ` · close ${formatDate(o.expected_close_date)}` : ""}
                      </div>
                    </div>
                    <span
                      className="badge"
                      style={{ background: c.bg, color: c.fg, textTransform: "capitalize" }}
                    >
                      {o.stage}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          <form onSubmit={handleAddOpp} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <input
              type="text"
              placeholder="Opportunity name"
              value={oppName}
              onChange={(e) => setOppName(e.target.value)}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="Amount"
                value={oppAmount}
                onChange={(e) => setOppAmount(e.target.value)}
                style={{ flex: 1 }}
              />
              <select
                value={oppStage}
                onChange={(e) => setOppStage(e.target.value as OpportunityStage)}
                style={{ flex: 1, textTransform: "capitalize" }}
              >
                {OPPORTUNITY_STAGES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <input
              type="date"
              value={oppClose}
              onChange={(e) => setOppClose(e.target.value)}
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={addingOpp}>
              {addingOpp ? "Saving…" : "New opportunity"}
            </button>
          </form>
        </div>

        {/* Log Activity */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: 12 }}>
            Log Activity
          </div>
          <form onSubmit={handleLogActivity} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <select
              value={actType}
              onChange={(e) => setActType(e.target.value as ActivityType)}
              style={{ textTransform: "capitalize" }}
            >
              {ACTIVITY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Subject"
              value={actSubject}
              onChange={(e) => setActSubject(e.target.value)}
            />
            <textarea
              placeholder="Details (optional)"
              value={actBody}
              onChange={(e) => setActBody(e.target.value)}
              rows={3}
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={loggingAct}>
              {loggingAct ? "Logging…" : "Log activity"}
            </button>
          </form>
          <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 0 }}>
            Logged activities appear in the timeline below.
          </p>
        </div>
      </div>

      {/* Tasks + Activity Timeline */}
      <div className="grid-2" style={{ marginBottom: 24, alignItems: "start" }}>
        {/* Tasks panel */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: 12 }}>
            Tasks
          </div>

          <form onSubmit={handleAddTask} style={{ marginBottom: 16 }}>
            <input
              type="text"
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
              placeholder="Task title…"
              style={{ marginBottom: 8 }}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <select
                value={taskPriority}
                onChange={(e) => setTaskPriority(e.target.value as TaskPriority)}
                style={{ flex: 1 }}
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
              </select>
              <input
                type="date"
                value={taskDue}
                onChange={(e) => setTaskDue(e.target.value)}
                style={{ flex: 1 }}
              />
              <button type="submit" className="btn btn-primary btn-sm" disabled={addingTask}>
                {addingTask ? "…" : "Add"}
              </button>
            </div>
          </form>

          {profile.tasks.length === 0 ? (
            <p style={{ color: "var(--color-text-muted)", fontSize: 14 }}>No tasks yet.</p>
          ) : (
            profile.tasks.map((task) => {
              const pc = PRIORITY_COLOR[task.priority] ?? PRIORITY_COLOR.normal;
              const done = task.status === "done";
              return (
                <div
                  key={task.id}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    padding: "10px 0",
                    borderBottom: "1px solid var(--color-border)",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={done}
                    disabled={updatingTaskId === task.id}
                    onChange={() => handleToggleTask(task)}
                    style={{ width: "auto", marginTop: 3, cursor: "pointer" }}
                  />
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontWeight: 600,
                        textDecoration: done ? "line-through" : "none",
                        color: done ? "var(--color-text-muted)" : "var(--color-text)",
                      }}
                    >
                      {task.title}
                    </div>
                    {task.description && (
                      <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                        {task.description}
                      </div>
                    )}
                    <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
                      <span className="badge" style={{ background: pc.bg, color: pc.fg, fontSize: 11 }}>
                        {task.priority}
                      </span>
                      {task.due_date && (
                        <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                          Due {formatDate(task.due_date)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Activity Timeline */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: 12 }}>
            Activity Timeline
          </div>
          {timeline.length === 0 ? (
            <p style={{ color: "var(--color-text-muted)", fontSize: 14 }}>No activity yet.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column" }}>
              {timeline.map((ev, i) => {
                const meta = TIMELINE_ICON[ev.type] ?? { icon: "•", color: "#6b7280" };
                return (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      gap: 12,
                      paddingBottom: i < timeline.length - 1 ? 16 : 0,
                      position: "relative",
                    }}
                  >
                    {/* connector line */}
                    {i < timeline.length - 1 && (
                      <div
                        style={{
                          position: "absolute",
                          left: 15,
                          top: 32,
                          bottom: 0,
                          width: 2,
                          background: "var(--color-border)",
                        }}
                      />
                    )}
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: meta.color + "1a",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        zIndex: 1,
                        border: `1px solid ${meta.color}33`,
                      }}
                    >
                      <span style={{ fontSize: 15 }}>{meta.icon}</span>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{ev.title}</div>
                      {ev.detail && (
                        <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                          {ev.detail}
                        </div>
                      )}
                      <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 2 }}>
                        {relativeTime(ev.ts)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Order history */}
      <div className="card" style={{ marginBottom: 24, padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px 12px" }}>
          <div className="card-title">Order History</div>
        </div>
        <div className="table-wrapper" style={{ border: "none", borderRadius: 0 }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: 24 }}></th>
                <th>Order ID</th>
                <th>Status</th>
                <th>Subtotal</th>
                <th>Tax &amp; Service</th>
                <th>Total</th>
                <th>Items</th>
              </tr>
            </thead>
            <tbody>
              {profile.orders.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 20 }}>
                    No orders
                  </td>
                </tr>
              ) : (
                profile.orders.map((o) => {
                  const open = expandedOrderId === o.id;
                  return (
                  <Fragment key={o.id}>
                  <tr
                    onClick={() => setExpandedOrderId(open ? null : o.id)}
                    style={{ cursor: "pointer" }}
                    title="Click to see full order detail"
                  >
                    <td style={{ color: "var(--color-text-muted)", textAlign: "center" }}>{open ? "▾" : "▸"}</td>
                    <td>
                      <code style={{ fontSize: 12 }}>{o.id.slice(0, 8)}…</code>
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: o.status === "completed" ? "#dcfce7" : "#fef9c3",
                          color: o.status === "completed" ? "#166534" : "#854d0e",
                        }}
                      >
                        {o.status}
                      </span>
                    </td>
                    <td>{formatSGD(o.subtotal)}</td>
                    <td>{formatSGD(o.service_charge + o.tax)}</td>
                    <td style={{ fontWeight: 700 }}>{formatSGD(o.total)}</td>
                    <td style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                      {o.items.map((i) => i.name_snapshot).join(", ")}
                    </td>
                  </tr>
                  {open && (
                    <tr>
                      <td colSpan={7} style={{ background: "var(--color-surface-alt, #f8fafc)", padding: "12px 20px" }}>
                        <table style={{ width: "100%", fontSize: 13 }}>
                          <tbody>
                            {o.items.map((it, idx) => (
                              <tr key={idx}>
                                <td style={{ padding: "2px 0" }}>
                                  <strong>{it.quantity}×</strong> {it.name_snapshot}
                                  {it.modifiers && it.modifiers.length > 0 && (
                                    <span style={{ color: "var(--color-text-muted)" }}>
                                      {" "}— {it.modifiers.map((m: { name: string; price_delta?: number }) => m.name).join(", ")}
                                    </span>
                                  )}
                                  <span style={{ color: "var(--color-text-muted)" }}> @ {formatSGD(it.unit_price)}</span>
                                </td>
                                <td style={{ textAlign: "right" }}>{formatSGD(it.line_total)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        <div style={{ borderTop: "1px dashed var(--color-border)", marginTop: 8, paddingTop: 8, fontSize: 13, maxWidth: 280, marginLeft: "auto" }}>
                          {([["Subtotal", o.subtotal], ["Service charge", o.service_charge], ["GST", o.tax]] as [string, number][]).map(([label, val]) => (
                            <div key={label} style={{ display: "flex", justifyContent: "space-between", color: "var(--color-text-muted)" }}>
                              <span>{label}</span><span>{formatSGD(val)}</span>
                            </div>
                          ))}
                          <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, marginTop: 2 }}>
                            <span>Total</span><span>{formatSGD(o.total)}</span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                  </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transaction history */}
      <div className="card" style={{ marginBottom: 24, padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px 12px" }}>
          <div className="card-title">Transaction History</div>
        </div>
        <div className="table-wrapper" style={{ border: "none", borderRadius: 0 }}>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Date</th>
                <th>Method</th>
                <th>Amount</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {profile.transactions.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 20 }}>
                    No transactions
                  </td>
                </tr>
              ) : (
                profile.transactions.map((t) => (
                  <tr key={t.id}>
                    <td><code style={{ fontSize: 12 }}>{t.id.slice(0, 8)}…</code></td>
                    <td style={{ fontSize: 13 }}>{formatDate(t.created_at)}</td>
                    <td>{t.method.toUpperCase()}</td>
                    <td style={{ fontWeight: 700 }}>{formatSGD(t.amount)}</td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: t.status === "success" ? "#dcfce7" : "#fef2f2",
                          color: t.status === "success" ? "#166534" : "#991b1b",
                        }}
                      >
                        {t.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rewards */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px 12px" }}>
          <div className="card-title">Loyalty Rewards History</div>
        </div>
        <div className="table-wrapper" style={{ border: "none", borderRadius: 0 }}>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Coins</th>
                <th>Reason</th>
                <th>Rule</th>
              </tr>
            </thead>
            <tbody>
              {profile.rewards.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 20 }}>
                    No rewards yet
                  </td>
                </tr>
              ) : (
                profile.rewards.map((r, i) => (
                  <tr key={i}>
                    <td style={{ fontSize: 13 }}>{formatDate(r.created_at)}</td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: r.txn_type === "earn" ? "#dcfce7" : "#fef2f2",
                          color: r.txn_type === "earn" ? "#166534" : "#991b1b",
                        }}
                      >
                        {r.txn_type}
                      </span>
                    </td>
                    <td style={{ fontWeight: 700, color: r.points > 0 ? "#16a34a" : "#dc2626" }}>
                      {r.points > 0 ? "+" : ""}
                      {r.points}
                    </td>
                    <td style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{r.reason ?? "—"}</td>
                    <td style={{ fontSize: 12 }}><code>{r.rule_code ?? "—"}</code></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </SidebarLayout>
  );
}
