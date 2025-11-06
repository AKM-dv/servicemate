import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "../services/apiClient.js";

const initialForm = {
  lead_id: "",
  plan_id: "",
  notes: "",
  setup_discount: "0",
};

const InvoicesPage = () => {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(initialForm);
  const [filters, setFilters] = useState({
    search: "",
    generated_from: "",
    generated_to: "",
  });
  const formatCurrency = (value) => `INR ${Number(value || 0).toLocaleString("en-IN")}`;
  const apiBase = apiClient.defaults.baseURL?.replace(/\/$/, "") || "";

  const { data: leads } = useQuery({
    queryKey: ["leads"],
    queryFn: () => apiClient.get("/leads").then((res) => res.data),
  });

  const { data: plans } = useQuery({
    queryKey: ["plans"],
    queryFn: () => apiClient.get("/plans").then((res) => res.data),
  });

  const { data: invoices } = useQuery({
    queryKey: ["invoices", filters],
    queryFn: () => {
      const params = {};
      if (filters.search) params.search = filters.search;
      if (filters.generated_from) params.generated_from = filters.generated_from;
      if (filters.generated_to) params.generated_to = filters.generated_to;
      return apiClient.get("/invoices", { params }).then((res) => res.data);
    },
  });

  const createInvoice = useMutation({
    mutationFn: (payload) => apiClient.post("/invoices", payload).then((res) => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      setForm(initialForm);
    },
  });

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    createInvoice.mutate({
      ...form,
      lead_id: Number(form.lead_id),
      plan_id: Number(form.plan_id),
      setup_discount: Number(form.setup_discount || 0),
    });
  };

  return (
    <div>
      <h2 className="section-heading">Generate Invoice</h2>
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="lead_id">Lead</label>
          <select id="lead_id" name="lead_id" value={form.lead_id} onChange={handleChange} required>
            <option value="">Select lead</option>
            {(leads || []).map((lead) => (
              <option key={lead.id} value={lead.id}>
                {lead.name || lead.phone}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="plan_id">Plan</label>
          <select id="plan_id" name="plan_id" value={form.plan_id} onChange={handleChange} required>
            <option value="">Select plan</option>
            {(plans || []).map((plan) => (
              <option key={plan.id} value={plan.id}>
                {plan.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="setup_discount">One-time Setup Discount (INR)</label>
          <input
            id="setup_discount"
            name="setup_discount"
            type="number"
            min="0"
            max="3000"
            value={form.setup_discount}
            onChange={handleChange}
          />
          <small style={{ color: "#64748b" }}>Default setup fee is INR 3,000. Enter discount to reduce it for this invoice.</small>
        </div>
        <div className="form-group" style={{ gridColumn: "1 / -1" }}>
          <label htmlFor="notes">Notes</label>
          <textarea id="notes" name="notes" rows="3" value={form.notes} onChange={handleChange} />
        </div>
        <div>
          <button className="btn btn-primary" type="submit" disabled={createInvoice.isPending}>
            {createInvoice.isPending ? "Creating..." : "Create Invoice"}
          </button>
        </div>
      </form>

      <h2 className="section-heading" style={{ marginTop: 40 }}>
        Invoices
      </h2>
      <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Lead</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Plan</th>
              <th>Setup Fee</th>
              <th>Discount</th>
              <th>Total</th>
              <th>Date</th>
              <th>PDF</th>
            </tr>
          </thead>
          <tbody>
            {(invoices || []).map((invoice) => {
              const viewUrl = invoice.pdf_url
                ? invoice.pdf_url.startsWith("http")
                  ? invoice.pdf_url
                  : `${apiBase}${invoice.pdf_url}`
                : null;
              const downloadUrl = viewUrl
                ? `${viewUrl}${viewUrl.includes("?") ? "&" : "?"}download=1`
                : null;

              return (
                <tr key={invoice.id}>
                  <td>{invoice.invoice_number}</td>
                  <td>{invoice.lead_name || invoice.lead_phone || "NA"}</td>
                  <td>{invoice.lead_email || "NA"}</td>
                  <td>{invoice.lead_phone || "NA"}</td>
                  <td>{invoice.plan_name}</td>
                  <td>{formatCurrency(invoice.setup_fee_amount || 0)}</td>
                  <td>{formatCurrency(invoice.setup_fee_discount || 0)}</td>
                  <td>{formatCurrency(invoice.total)}</td>
                  <td>{invoice.generated_at ? new Date(invoice.generated_at).toLocaleString() : "--"}</td>
                  <td>
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
                      "Pending"
                    )}
                  </td>
                </tr>
              );
            })}
            {(!invoices || invoices.length === 0) && (
              <tr>
                <td colSpan="10" style={{ textAlign: "center", padding: 40 }}>
                  No invoices yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default InvoicesPage;

