import PropTypes from "prop-types";

const STATUS_PALETTE = {
  "new": { backgroundColor: "#E0F2FE", color: "#0C4A6E" },
  "in-progress": { backgroundColor: "#FEF08A", color: "#78350F" },
  "converted": { backgroundColor: "#DCFCE7", color: "#14532D" },
  "lost": { backgroundColor: "#FEE2E2", color: "#7F1D1D" },
  "contacted": { backgroundColor: "#DBEAFE", color: "#1E3A8A" },
  "meeting-scheduled": { backgroundColor: "#DDD6FE", color: "#4C1D95" },
  "negotiation": { backgroundColor: "#FFE4E6", color: "#9D174D" },
  "closed-won": { backgroundColor: "#DCFCE7", color: "#14532D" },
  "closed-lost": { backgroundColor: "#FEE2E2", color: "#7F1D1D" },
  "custom": { backgroundColor: "#1D4ED8", color: "#EFF6FF" },
  "open": { backgroundColor: "#DBEAFE", color: "#1E3A8A" },
  "in-review": { backgroundColor: "#FEF3C7", color: "#92400E" },
  "resolved": { backgroundColor: "#D1FAE5", color: "#065F46" },
};

const StatusBadge = ({ value }) => {
  const normalized = (value || "NA").toString().trim();
  const key = normalized.toLowerCase().replace(/\s+/g, "-");
  const palette = STATUS_PALETTE[key] || { backgroundColor: "#E2E8F0", color: "#1E293B" };

  return (
    <span className="status-badge" style={palette}>
      {normalized || "NA"}
    </span>
  );
};

StatusBadge.propTypes = {
  value: PropTypes.string,
};

export default StatusBadge;

