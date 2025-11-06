import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import apiClient from "../services/apiClient.js";

const DEFAULT_INVOICE = {
  invoice_number: "INV_20251107_0001",
  plan_name: "Basic",
  plan_price: 1999,
  setup_fee_amount: 3000,
  setup_fee_discount: 0,
  subtotal: 4999,
  total: 4999,
  lead_name: "Demo Client",
  lead_phone: "+91 9876543210",
  lead_email: "demo@example.com",
  lead_address: "123 Sample Street, Jaipur, Rajasthan",
  brand_name: "Demo Brand",
  generated_at: new Date().toISOString(),
};

const NEIGH_LOGO = "/logo.png";
const REMOTE_NEIGH_LOGO =
  "https://github.com/AKM-dv/servicemate/blob/main/logo-details%202.png?raw=true";
const UPI_QR =
  "https://github.com/AKM-dv/servicemate/blob/main/WhatsApp%20Image%202025-11-07%20at%2001.24.34.jpeg?raw=true";

const InvoicePreviewPage = () => {
  const { data: invoices } = useQuery({
    queryKey: ["invoices", "preview"],
    queryFn: () => apiClient.get("/invoices").then((res) => res.data),
  });

  const [selectedIndex, setSelectedIndex] = useState(0);

  const invoice = useMemo(() => {
    if (!invoices || invoices.length === 0) {
      return DEFAULT_INVOICE;
    }
    return invoices[Math.min(selectedIndex, invoices.length - 1)];
  }, [invoices, selectedIndex]);

  const setupDiscount = Number(invoice.setup_fee_discount || 0);
  const setupFee = Number(invoice.setup_fee_amount || 0);
  const planPrice = Number(invoice.plan_price || invoice.subtotal || 0);

  return (
    <div className="invoice-preview-page">
      <div className="invoice-preview-toolbar">
        <div>
          <h2 className="section-heading" style={{ marginBottom: 12 }}>
            Invoice Preview
          </h2>
          <p>Review the layout the PDF generator uses. Select an invoice to preview its data.</p>
        </div>
        <div className="invoice-preview-selector">
          {invoices && invoices.length > 0 ? (
            <select
              value={selectedIndex}
              onChange={(event) => setSelectedIndex(Number(event.target.value))}
            >
              {invoices.map((item, index) => (
                <option key={item.id} value={index}>
                  {item.invoice_number}
                </option>
              ))}
            </select>
          ) : (
            <span className="preview-badge">Using example data</span>
          )}
        </div>
      </div>

      <div className="invoice-preview-canvas">
        <div className="invoice-sheet">
          <header className="invoice-header">
            <img
              src={NEIGH_LOGO}
              onError={(event) => {
                if (event.currentTarget.src !== REMOTE_NEIGH_LOGO) {
                  event.currentTarget.src = REMOTE_NEIGH_LOGO;
                }
              }}
              alt="Neighshop Global"
              className="invoice-header-logo"
            />
            <div className="invoice-header-text">
              <h1>Neighshop Global</h1>
              <p>
                Shri Ram Nagar, 8-B, opp. Dhanwantri Hospital & Research Centre, near New Sanganer
                Road, Mansarovar, Jaipur, Rajasthan 302020
              </p>
              <p className="invoice-header-contact">+91 8307802643</p>
            </div>
          </header>

          <section className="invoice-meta">
            <div>
              <span className="meta-label">Invoice #</span>
              <span className="meta-value">{invoice.invoice_number}</span>
            </div>
            <div>
              <span className="meta-label">Invoice Date</span>
              <span className="meta-value">
                {invoice.generated_at ? new Date(invoice.generated_at).toLocaleDateString() : "--"}
              </span>
            </div>
            <div>
              <span className="meta-label">Plan</span>
              <span className="meta-value">{invoice.plan_name || "Basic"}</span>
            </div>
          </section>

          <section className="invoice-client">
            <div>
              <span className="meta-label">Client</span>
              <span className="meta-value">{invoice.lead_name || invoice.lead_phone || "--"}</span>
            </div>
            <div>
              <span className="meta-label">Brand</span>
              <span className="meta-value">{invoice.brand_name || "--"}</span>
            </div>
            <div>
              <span className="meta-label">Email</span>
              <span className="meta-value">{invoice.lead_email || "--"}</span>
            </div>
            <div>
              <span className="meta-label">Phone</span>
              <span className="meta-value">{invoice.lead_phone || "--"}</span>
            </div>
            <div>
              <span className="meta-label">Address</span>
              <span className="meta-value">{invoice.lead_address || "--"}</span>
            </div>
          </section>

          <section className="invoice-table">
            <table>
              <thead>
                <tr>
                  <th>Description</th>
                  <th>Amount (INR)</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Plan - {invoice.plan_name || "Basic"}</td>
                  <td>{planPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                </tr>
                <tr>
                  <td>One-time Setup Fee</td>
                  <td>{setupFee.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                </tr>
                {setupDiscount > 0 && (
                  <tr>
                    <td>One-time Discount</td>
                    <td>-{setupDiscount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                  </tr>
                )}
                <tr>
                  <td>Subtotal</td>
                  <td>{Number(invoice.subtotal || planPrice + setupFee - setupDiscount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                </tr>
                <tr>
                  <td>Grand Total</td>
                  <td>{Number(invoice.total || planPrice + setupFee - setupDiscount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section className="invoice-payment">
            <div>
              <h3>Payment Details</h3>
              <ul>
                <li>Bank Name: STATE BANK OF INDIA</li>
                <li>Account Holder: Suman Kumari</li>
                <li>Account Number: 42213259870</li>
                <li>UPI: 8307802643@axl</li>
              </ul>
            </div>
            <div className="invoice-qr">
              <img src={UPI_QR} alt="UPI QR" />
              <span>Scan UPI: 8307802643@axl</span>
            </div>
          </section>

          <footer className="invoice-footer">
            Thank you for choosing Neighshop Global.
          </footer>
        </div>
      </div>
    </div>
  );
};

export default InvoicePreviewPage;
