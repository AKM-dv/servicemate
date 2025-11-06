import { NavLink, Outlet } from "react-router-dom";
import PropTypes from "prop-types";
import { FiHome, FiUsers, FiFileText, FiSettings, FiMessageSquare, FiEye } from "react-icons/fi";
import { useAuth } from "../context/AuthContext.jsx";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: FiHome },
  { path: "/leads", label: "Leads", icon: FiUsers },
  { path: "/plans", label: "Plans", icon: FiSettings },
  { path: "/invoices", label: "Invoices", icon: FiFileText },
  { path: "/invoice-preview", label: "Invoice Preview", icon: FiEye },
  { path: "/feedback", label: "Feedback", icon: FiMessageSquare },
];

const SERVICEMATE_LOGO = "https://github.com/AKM-dv/servicemate/blob/main/Group%2064.png?raw=true";
const NEIGHSHOP_LOGO = "https://github.com/AKM-dv/servicemate/blob/main/logo-details%202.png?raw=true";

const Layout = ({ children }) => {
  const { logout } = useAuth();
  const content = children ?? <Outlet />;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img src={SERVICEMATE_LOGO} alt="Service Mate" className="brand-logo" />
          <span>Service Mate</span>
        </div>
        <nav className="nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `nav-item${isActive ? " nav-item-active" : ""}`
                }
              >
                <Icon className="nav-item-icon" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </aside>
      <main className="main-content">
        <header className="top-bar">
          <div className="top-bar-details">
            <div className="top-bar-branding">
              <img src={NEIGHSHOP_LOGO} alt="Neighshop Global" className="top-brand-logo" />
              <div>
                <h1 className="page-title">Service Mate CRM</h1>
                <p className="page-subtitle">Powered by Neighshop Global</p>
              </div>
            </div>
          </div>
          <button className="btn btn-secondary" type="button" onClick={logout}>
            Logout
          </button>
        </header>
        <section className="page-content">{content}</section>
      </main>
    </div>
  );
};

Layout.propTypes = {
  children: PropTypes.node,
};

export default Layout;

