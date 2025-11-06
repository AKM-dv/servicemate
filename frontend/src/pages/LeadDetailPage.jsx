import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import apiClient from "../services/apiClient.js";
import StatusBadge from "../components/StatusBadge.jsx";

const followupInitial = {
  status: "Contacted",
  follow_up_date: "",
  objective: "",
  next_follow_up: "",
  future_follow_up_note: "",
  note: "",
};

const LeadDetailPage = () => {
  const { leadId } = useParams();
  const queryClient = useQueryClient();
  const apiBase = apiClient.defaults.baseURL?.replace(/\/$/, "") || "";
  const [followupForm, setFollowupForm] = useState(() => ({
    ...followupInitial,
    follow_up_date: new Date().toISOString().slice(0, 10),
  }));
  const [editForm, setEditForm] = useState({
    name: "",
    email: "",
    phone: "",
    brand_name: "",
    address: "",
    status: "New",
    preferred_plan_id: "",
  });

  const formatCurrency = (value) => `INR ${Number(value || 0).toLocaleString("en-IN")}`;

  const { data: lead, isLoading } = useQuery({
    queryKey: ["leads", leadId],
    queryFn: () => apiClient.get(`/leads/${leadId}`).then((res) => res.data),
  });

  const { data: plans } = useQuery({
    queryKey: ["plans"],
    queryFn: () => apiClient.get("/plans").then((res) => res.data),
  });

  const followupMutation = useMutation({
    mutationFn: (payload) =>
      apiClient
        .post(`/leads/${leadId}/followups`, payload)
        .then((res) => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads", leadId] });
      setFollowupForm({
        ...followupInitial,
        follow_up_date: new Date().toISOString().slice(0, 10),
      });
    },
  });

  const updateLeadMutation = useMutation({
    mutationFn: (payload) =>
      apiClient
        .put(`/leads/${leadId}`, payload)
        .then((res) => res.data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["leads", leadId] });
      setEditForm({
        name: data.name || "",
        email: data.email || "",
        phone: data.phone || "",
        brand_name: data.brand_name || "",
        address: data.address || "",
        status: data.status || "New",
        preferred_plan_id: data.preferred_plan_id ? String(data.preferred_plan_id) : "",
      });
    },
  });

  useEffect(() => {
    if (lead) {
      setEditForm({
        name: lead.name || "",
        email: lead.email || "",
        phone: lead.phone || "",
        brand_name: lead.brand_name || "",
        address: lead.address || "",
        status: lead.status || "New",
        preferred_plan_id: lead.preferred_plan_id ? String(lead.preferred_plan_id) : "",
      });
    }
  }, [lead]);

  if (isLoading) {
    return <div>Loading lead...</div>;
  }

  if (!lead) {
    return <div>Lead not found.</div>;
  }

  const handleFollowupChange = (event) => {
    const { name, value } = event.target;
    setFollowupForm((prev) => ({ ...prev, [name]: value }));
  };

  const submitFollowup = (event) => {
    event.preventDefault();
    const isClosed = followupForm.status === "Closed Won" || followupForm.status === "Closed Lost";
    followupMutation.mutate({
      ...followupForm,
      follow_up_date: followupForm.follow_up_date || new Date().toISOString().slice(0, 10),
      next_follow_up: isClosed ? null : followupForm.next_follow_up || null,
      future_follow_up_note: isClosed ? null : followupForm.future_follow_up_note || null,
    });
  };

  const leadTitle = lead.name || lead.phone || "Lead";
  const isClosedStatus =
    followupForm.status === "Closed Won" || followupForm.status === "Closed Lost";

  const handleEditChange = (event) => {
    const { name, value } = event.target;
    setEditForm((prev) => ({ ...prev, [name]: value }));
  };

  const submitLeadUpdate = (event) => {
    event.preventDefault();
    updateLeadMutation.mutate({
      name: editForm.name || null,
      email: editForm.email || null,
      phone: editForm.phone,
      brand_name: editForm.brand_name || null,
      address: editForm.address || null,
      status: editForm.status,
      preferred_plan_id: editForm.preferred_plan_id ? Number(editForm.preferred_plan_id) : null,
    });
  };

  return (
    <div className="lead-detail">
      <h2 className="section-heading">{leadTitle}</h2>
      <div className="card-grid" style={{ marginBottom: 32 }}>
        <div className="card">
          <div className="card-title">Email</div>
          <div>{lead.email || "NA"}</div>
        </div>
        <div className="card">
          <div className="card-title">Phone</div>
          <div>{lead.phone || "NA"}</div>
        </div>
        <div className="card">
          <div className="card-title">Brand</div>
          <div>{lead.brand_name || "NA"}</div>
        </div>
        <div className="card">
          <div className="card-title">Status</div>
          <StatusBadge value={lead.status} />
        </div>
        <div className="card">
          <div className="card-title">Preferred Plan</div>
          <div>{lead.preferred_plan_name || "NA"}</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 32 }}>
        <div className="card-title">Update Lead Details</div>
        <form className="form-grid" onSubmit={submitLeadUpdate}>
          <div className="form-group">
            <label htmlFor="edit_phone">Phone *</label>
            <input
              id="edit_phone"
              name="phone"
              value={editForm.phone}
              onChange={handleEditChange}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="edit_name">Name</label>
            <input id="edit_name" name="name" value={editForm.name} onChange={handleEditChange} />
          </div>
          <div className="form-group">
            <label htmlFor="edit_email">Email</label>
            <input
              id="edit_email"
              name="email"
              type="email"
              value={editForm.email}
              onChange={handleEditChange}
            />
          </div>
          <div className="form-group">
            <label htmlFor="edit_brand">Brand Name</label>
            <input
              id="edit_brand"
              name="brand_name"
              value={editForm.brand_name}
              onChange={handleEditChange}
            />
          </div>
          <div className="form-group">
            <label htmlFor="edit_address">Address</label>
            <textarea
              id="edit_address"
              name="address"
              rows="2"
              value={editForm.address}
              onChange={handleEditChange}
            />
          </div>
          <div className="form-group">
            <label htmlFor="edit_status">Status</label>
            <select id="edit_status" name="status" value={editForm.status} onChange={handleEditChange}>
              <option value="New">New</option>
              <option value="In Progress">In Progress</option>
              <option value="Converted">Converted</option>
              <option value="Lost">Lost</option>
              <option value="Custom">Custom</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="edit_plan">Preferred Plan</label>
            <select
              id="edit_plan"
              name="preferred_plan_id"
              value={editForm.preferred_plan_id}
              onChange={handleEditChange}
            >
              <option value="">Not Known / NA</option>
              {(plans || []).map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.name}
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", alignItems: "flex-end" }}>
            <button className="btn btn-primary" type="submit" disabled={updateLeadMutation.isPending}>
              {updateLeadMutation.isPending ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>

      <div className="split-layout">
        <div>
          <div className="card followup-card" style={{ marginBottom: 24 }}>
            <div className="card-title">Add Follow-up</div>
            <form className="form-grid" onSubmit={submitFollowup}>
              <div className="form-group">
                <label htmlFor="follow_up_date">Follow-up Date</label>
                <input
                  id="follow_up_date"
                  name="follow_up_date"
                  type="date"
                  value={followupForm.follow_up_date}
                  onChange={handleFollowupChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="status">Status</label>
                <select
                  id="status"
                  name="status"
                  value={followupForm.status}
                  onChange={handleFollowupChange}
                >
                  <option value="Contacted">Contacted</option>
                  <option value="Meeting Scheduled">Meeting Scheduled</option>
                  <option value="Negotiation">Negotiation</option>
                  <option value="Closed Won">Closed Won</option>
                  <option value="Closed Lost">Closed Lost</option>
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="objective">Objective</label>
                <input
                  id="objective"
                  name="objective"
                  value={followupForm.objective}
                  onChange={handleFollowupChange}
                  placeholder="e.g., Demo call, Proposal review"
                />
              </div>
              <div className="form-group">
                <label htmlFor="next_follow_up">Next Follow-up</label>
                <input
                  id="next_follow_up"
                  name="next_follow_up"
                  type="date"
                  value={followupForm.next_follow_up}
                  onChange={handleFollowupChange}
                  disabled={isClosedStatus}
                />
              </div>
              <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                <label htmlFor="future_follow_up_note">Future Follow-up Notes</label>
                <textarea
                  id="future_follow_up_note"
                  name="future_follow_up_note"
                  rows="2"
                  value={followupForm.future_follow_up_note}
                  onChange={handleFollowupChange}
                  disabled={isClosedStatus}
                  placeholder="Reminder for next touchpoint"
                />
              </div>
              <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                <label htmlFor="note">Notes</label>
                <textarea
                  id="note"
                  name="note"
                  rows="3"
                  value={followupForm.note}
                  onChange={handleFollowupChange}
                />
              </div>
              <div>
                <button className="btn btn-primary" type="submit" disabled={followupMutation.isPending}>
                  {followupMutation.isPending ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </div>

          <div className="card">
            <div className="card-title">Follow-up Timeline</div>
            <div className="followup-list">
              {(lead.followups || []).map((item) => (
                <div key={item.id} className="followup-item">
                  <div className="followup-item-header">
                    <StatusBadge value={item.status} />
                    <span className="followup-date">
                      {item.follow_up_date ? new Date(item.follow_up_date).toLocaleDateString() : "--"}
                    </span>
                  </div>
                  {item.objective && (
                    <div className="followup-objective">Objective: {item.objective}</div>
                  )}
                  <div className="followup-notes">{item.note || "No notes"}</div>
                  <div className="followup-footer">
                    <span>
                      Created: {item.created_at ? new Date(item.created_at).toLocaleString() : "--"}
                    </span>
                    <span>
                      Next: {item.next_follow_up ? new Date(item.next_follow_up).toLocaleDateString() : "--"}
                    </span>
                  </div>
                  {item.future_follow_up_note && (
                    <div className="followup-future-note">
                      Future Note: {item.future_follow_up_note}
                    </div>
                  )}
                </div>
              ))}
              {(!lead.followups || lead.followups.length === 0) && (
                <div className="followup-empty">No follow-ups yet.</div>
              )}
            </div>
          </div>
        </div>

        <div>
          <div className="card" style={{ marginTop: 0 }}>
            <div className="card-title">Invoices</div>
            <div className="followup-list">
              {(lead.invoices || []).map((invoice) => {
                const viewUrl = invoice.pdf_url
                  ? invoice.pdf_url.startsWith("http")
                    ? invoice.pdf_url
                    : `${apiBase}${invoice.pdf_url}`
                  : null;
                const downloadUrl = viewUrl
                  ? `${viewUrl}${viewUrl.includes("?") ? "&" : "?"}download=1`
                  : null;

                return (
                  <div key={invoice.id} className="followup-item">
                    <div className="followup-item-header">
                      <div style={{ fontWeight: 600 }}>{invoice.invoice_number}</div>
                      <span className="followup-date">
                        {invoice.generated_at ? new Date(invoice.generated_at).toLocaleString() : "--"}
                      </span>
                    </div>
                    <div className="followup-notes">Amount: {formatCurrency(invoice.total)}</div>
                    {viewUrl ? (
                      <div className="table-actions">
                        <a className="btn btn-link" href={viewUrl} target="_blank" rel="noreferrer">
                          View
                        </a>
                        <a className="btn btn-secondary" href={downloadUrl} target="_blank" rel="noreferrer">
                          Download
                        </a>
                      </div>
                    ) : (
                      <div className="followup-empty" style={{ padding: "12px", marginTop: "8px" }}>
                        PDF pending generation
                      </div>
                    )}
                  </div>
                );
              })}
              {(!lead.invoices || lead.invoices.length === 0) && (
                <div className="followup-empty">No invoices yet.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LeadDetailPage;

