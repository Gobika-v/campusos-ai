import { useState, useRef, useEffect } from "react";
import axios from "axios";
import DecisionDemo from "./DecisionDemo";
import {
  LayoutDashboard,
  Bot,
  GraduationCap,
  CalendarDays,
  Wrench,
  Wallet,
  Send,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Clock,
  Percent,
  FileText,
  BadgeIndianRupee,
  Cpu,
  Zap,
  ChevronRight,
} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "assistant", label: "AI Assistant", icon: Bot },
  { key: "academics", label: "Academics", icon: GraduationCap },
  { key: "events", label: "Events", icon: CalendarDays },
  { key: "maintenance", label: "Maintenance", icon: Wrench },
  { key: "finance", label: "Finance", icon: Wallet },
];

const INITIAL_AGENTS = [
  { key: "academic", name: "Academic Agent", icon: GraduationCap, status: "Ready" },
  { key: "examination", name: "Examination Agent", icon: FileText, status: "Ready" },
  { key: "events", name: "Events Agent", icon: CalendarDays, status: "Ready" },
  { key: "administration", name: "Administration Agent", icon: FileText, status: "Ready" },
  { key: "maintenance", name: "Maintenance Agent", icon: Wrench, status: "Ready" },
  { key: "grievance", name: "Grievance Agent", icon: AlertTriangle, status: "Ready" },
  { key: "finance", name: "Finance Agent", icon: Wallet, status: "Ready" },
];

const QUICK_PROMPTS = [
  "What is my timetable?",
  "Show my attendance",
  "Find AI workshops",
  "The projector in Room 302 is broken",
];

function agentKeyFromName(agentName) {
  if (!agentName) return null;
  const normalized = agentName.toLowerCase();
  if (normalized.includes("academic")) return "academic";
  if (normalized.includes("examination") || normalized.includes("exam")) return "examination";
  if (normalized.includes("event")) return "events";
  if (normalized.includes("admin")) return "administration";
  if (normalized.includes("maintenance")) return "maintenance";
  if (normalized.includes("grievance")) return "grievance";
  if (normalized.includes("finance")) return "finance";
  return null;
}

function StatusBadge({ tone, children }) {
  return <span className={`status-badge status-badge--${tone}`}>{children}</span>;
}

function LoadingDots() {
  return (
    <span className="loading-dots" aria-label="Loading">
      <span className="loading-dots__dot" />
      <span className="loading-dots__dot" />
      <span className="loading-dots__dot" />
    </span>
  );
}

function AgentDataBlock({ data }) {
  if (data === null || data === undefined) return null;

  if (Array.isArray(data)) {
    return (
      <div className="data-block data-block--list">
        {data.map((item, idx) => (
          <div className="data-block__list-item" key={idx}>
            {typeof item === "object" ? <AgentDataBlock data={item} /> : String(item)}
          </div>
        ))}
      </div>
    );
  }

  if (typeof data === "object") {
    return (
      <div className="data-block">
        {Object.entries(data).map(([key, value]) => (
          <div className="data-block__row" key={key}>
            <span className="data-block__key">{key.replace(/_/g, " ")}</span>
            <span className="data-block__value">
              {typeof value === "object" && value !== null ? (
                <AgentDataBlock data={value} />
              ) : (
                String(value)
              )}
            </span>
          </div>
        ))}
      </div>
    );
  }

  return <div className="data-block data-block--plain">{String(data)}</div>;
}

export default function App() {
  const [activeNav, setActiveNav] = useState("dashboard");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text:
        "Hi Arjun. I can coordinate your timetable, attendance, events, fees and campus requests.",
      agent: null,
      toolsUsed: [],
      data: null,
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState(null);
  const [agents, setAgents] = useState(INITIAL_AGENTS);
  const [lastToolsUsed, setLastToolsUsed] = useState([]);
  const [pendingIntent, setPendingIntent] = useState(null);

  const [ticketForm, setTicketForm] = useState({
    location: "",
    issue: "",
    priority: "medium",
  });
  const [ticketStatus, setTicketStatus] = useState("idle"); // idle | loading | success | error
  const [ticketResult, setTicketResult] = useState(null);
  const [ticketError, setTicketError] = useState(null);
  const [registrationStatus, setRegistrationStatus] = useState("idle");
  const [registrationError, setRegistrationError] = useState(null);
  const [registrationResult, setRegistrationResult] = useState(null);

  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function sendMessage(text) {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;

    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setInputValue("");
    setIsSending(true);
    setChatError(null);

    try {
      const requestMessage = pendingIntent === "leave_request"
        ? `leave request ${trimmed}`
        : trimmed;
      const response = await axios.post(`${API_BASE_URL}/api/chat`, {
        student_id: 1,
        message: requestMessage,
      });

      const payload = response.data || {};
      const agentKey = agentKeyFromName(payload.agent);

      setAgents((prev) =>
        prev.map((a) => ({
          ...a,
          status: a.key === agentKey ? "Active" : "Ready",
        }))
      );
      setLastToolsUsed(payload.tools_used || []);
      if (payload.action_id) {
        setPendingIntent(null);
      } else if (payload.agent?.toLowerCase().includes("administration")) {
        setPendingIntent("leave_request");
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: payload.message || "I've processed your request.",
          agent: payload.agent || null,
          toolsUsed: payload.tools_used || [],
          data: payload.data ?? null,
        },
      ]);
    } catch {
      setChatError(
        "CampusOS AI backend is unavailable right now. Please check the server and try again."
      );
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    sendMessage(inputValue);
  }

  async function handleCreateTicket(e) {
    e.preventDefault();
    if (!ticketForm.location.trim() || !ticketForm.issue.trim()) return;

    setTicketStatus("loading");
    setTicketError(null);
    setTicketResult(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/maintenance/ticket`, {
        location: ticketForm.location,
        issue: ticketForm.issue,
        priority: ticketForm.priority,
      });
      setTicketResult(response.data);
      setTicketStatus("success");
    } catch {
      setTicketError("Could not create the ticket. Please check the backend connection.");
      setTicketStatus("error");
    }
  }

  async function handleAnalyzeRegistration() {
    setRegistrationStatus("analyzing");
    setRegistrationError(null);
    setRegistrationResult(null);

    try {
      await axios.get(`${API_BASE_URL}/api/events/search?query=AI`);
      await axios.get(`${API_BASE_URL}/api/academic/timetable?student_id=1`);
      await axios.get(`${API_BASE_URL}/api/academic/attendance?student_id=1`);
      setRegistrationStatus("confirmation");
    } catch {
      setRegistrationError(
        "Could not complete the registration analysis. Please check the backend connection and try again."
      );
      setRegistrationStatus("error");
    }
  }

  function handleCancelRegistration() {
    setRegistrationStatus("idle");
    setRegistrationError(null);
    setRegistrationResult(null);
  }

  async function handleRegisterAndApplyLeave() {
    setRegistrationStatus("registering");
    setRegistrationError(null);

    try {
      const registrationResponse = await axios.post(
        `${API_BASE_URL}/api/events/register`,
        {
          student_id: 1,
          event_id: 1,
        }
      );
      const leaveResponse = await axios.post(`${API_BASE_URL}/api/admin/leave`, {
        student_id: 1,
        start_date: "2026-08-23",
        end_date: "2026-08-23",
        reason: "Academic event leave: AI Innovation Workshop",
      });

      setRegistrationResult({
        eventActionId: registrationResponse.data?.action_id || "N/A",
        leaveActionId: leaveResponse.data?.action_id || "N/A",
      });
      setRegistrationStatus("success");
    } catch (err) {
      if (err.response?.status === 409) {
        setRegistrationError(
          "You are already registered for this workshop. No duplicate registration was created."
        );
      } else {
        setRegistrationError(
          "Could not register for the workshop and submit the leave request. Please try again."
        );
      }
      setRegistrationStatus("error");
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <div className="sidebar__logo">
            <Cpu size={22} />
          </div>
          <div>
            <div className="sidebar__title">CampusOS AI</div>
            <div className="sidebar__subtitle">Autonomous Campus Operations</div>
          </div>
        </div>

        <nav className="sidebar__nav">
          {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              className={`nav-item ${activeNav === key ? "nav-item--active" : ""}`}
              onClick={() => setActiveNav(key)}
              type="button"
            >
              <Icon size={18} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar__student-card">
          <div className="sidebar__student-avatar">AM</div>
          <div>
            <div className="sidebar__student-name">Arjun Mehta</div>
            <div className="sidebar__student-meta">CSE • Semester 4</div>
            <div className="sidebar__student-id">CSE2024-041</div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="dashboard-header">
          <div>
            <h1 className="dashboard-header__title">Good morning, Arjun</h1>
            <p className="dashboard-header__subtitle">Your campus, coordinated by AI.</p>
          </div>
          <div className="status-pill">
            <span className="status-pill__dot" />
            All systems operational
          </div>
        </header>

        <section className="stat-grid">
          <div className="glass-card stat-card">
            <div className="stat-card__icon stat-card__icon--blue">
              <Clock size={18} />
            </div>
            <div className="stat-card__label">Next Class</div>
            <div className="stat-card__value">Machine Learning</div>
            <div className="stat-card__meta">11:00 AM • AI Lab-2</div>
          </div>

          <div className="glass-card stat-card">
            <div className="stat-card__icon stat-card__icon--purple">
              <Percent size={18} />
            </div>
            <div className="stat-card__label">Attendance</div>
            <div className="stat-card__value">78.3%</div>
            <StatusBadge tone="attention">Attention</StatusBadge>
          </div>

          <div className="glass-card stat-card">
            <div className="stat-card__icon stat-card__icon--blue">
              <FileText size={18} />
            </div>
            <div className="stat-card__label">Upcoming Exam</div>
            <div className="stat-card__value">DBMS Internal</div>
            <div className="stat-card__meta">Assessment</div>
          </div>

          <div className="glass-card stat-card">
            <div className="stat-card__icon stat-card__icon--purple">
              <BadgeIndianRupee size={18} />
            </div>
            <div className="stat-card__label">Pending Fee</div>
            <div className="stat-card__value">₹25,000</div>
            <div className="stat-card__meta">Due in 15 days</div>
          </div>
        </section>

        <section className="workspace-grid">
          <div className="glass-card assistant-panel">
            <div className="panel-heading">
              <Sparkles size={18} />
              <h2>Ask CampusOS AI</h2>
            </div>

            <div className="chat-history">
              {messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`chat-bubble-row chat-bubble-row--${m.role}`}
                >
                  <div className={`chat-bubble chat-bubble--${m.role}`}>
                    <div className="chat-bubble__text">{m.text}</div>
                    {m.role === "assistant" && (m.agent || (m.toolsUsed && m.toolsUsed.length > 0)) && (
                      <div className="chat-bubble__meta">
                        {m.agent && <span className="chat-bubble__agent">{m.agent}</span>}
                        {m.toolsUsed && m.toolsUsed.length > 0 && (
                          <span className="chat-bubble__tools">
                            {m.toolsUsed.join(" • ")}
                          </span>
                        )}
                      </div>
                    )}
                    {m.role === "assistant" && m.data && <AgentDataBlock data={m.data} />}
                  </div>
                </div>
              ))}

              {isSending && (
                <div className="chat-bubble-row chat-bubble-row--assistant">
                  <div className="chat-bubble chat-bubble--assistant chat-bubble--loading">
                    <LoadingDots />
                  </div>
                </div>
              )}

              {chatError && <div className="chat-error">{chatError}</div>}

              <div ref={chatEndRef} />
            </div>

            <div className="quick-prompts">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="quick-prompt-btn"
                  onClick={() => sendMessage(prompt)}
                  disabled={isSending}
                >
                  {prompt}
                </button>
              ))}
            </div>

            <form className="chat-input-row" onSubmit={handleSubmit}>
              <input
                type="text"
                className="chat-input"
                placeholder="Message CampusOS AI..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={isSending}
              />
              <button
                type="submit"
                className="chat-send-btn"
                disabled={isSending || !inputValue.trim()}
              >
                {isSending ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
              </button>
            </form>
          </div>

          <div className="glass-card agent-panel">
            <div className="panel-heading">
              <Zap size={18} />
              <h2>Agent Activity</h2>
            </div>

            <div className="agent-list">
              {agents.map((agent) => {
                const Icon = agent.icon;
                const isActive = agent.status === "Active";
                return (
                  <div
                    key={agent.key}
                    className={`agent-item ${isActive ? "agent-item--active" : ""}`}
                  >
                    <div className="agent-item__icon">
                      <Icon size={16} />
                    </div>
                    <div className="agent-item__name">{agent.name}</div>
                    <StatusBadge tone={isActive ? "active" : "ready"}>
                      {agent.status}
                    </StatusBadge>
                  </div>
                );
              })}
            </div>

            {lastToolsUsed.length > 0 && (
              <div className="tools-used">
                <div className="tools-used__label">Tools used</div>
                <div className="tools-used__chips">
                  {lastToolsUsed.map((tool, idx) => (
                    <span className="tool-chip" key={idx}>
                      <ChevronRight size={12} />
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="glass-card actions-panel">
          <div className="panel-heading">
            <CalendarDays size={18} />
            <h2>AI Workshop Smart Registration</h2>
          </div>

          <div className="ticket-result">
            <div>
              <div className="ticket-result__title">AI Innovation Workshop</div>
              <div className="ticket-result__id">
                Tomorrow • 2:00 PM–4:00 PM • Seminar Hall 1 • Event ID: 1
              </div>
            </div>
          </div>

          {registrationStatus === "idle" && (
            <button
              type="button"
              className="create-ticket-btn"
              onClick={handleAnalyzeRegistration}
            >
              Analyze &amp; Register
            </button>
          )}

          {registrationStatus === "analyzing" && (
            <div className="ticket-result">
              <Loader2 size={18} className="spin" />
              <div>Analyzing event, timetable, and attendance...</div>
            </div>
          )}

          {(registrationStatus === "confirmation" || registrationStatus === "registering") && (
            <>
              <div className="ticket-result">
                <div>
                  <div className="ticket-result__title">Agent Collaboration Timeline</div>
                  <div>Events Agent: Found AI Innovation Workshop, 2:00–4:00 PM</div>
                  <div>Academic Agent: Conflict found — DBMS class, 2:00–3:00 PM</div>
                  <div>Policy Agent: DBMS attendance is 89%, above 75% requirement</div>
                  <div>Administration Agent: Eligible to submit academic-event leave request</div>
                </div>
              </div>

              <div className="ticket-result">
                <div>
                  <div className="ticket-result__title">
                    Register for the AI Workshop and submit an event leave request?
                  </div>
                  <div className="maintenance-form">
                    <button
                      type="button"
                      className="create-ticket-btn"
                      onClick={handleRegisterAndApplyLeave}
                      disabled={registrationStatus === "registering"}
                    >
                      {registrationStatus === "registering" ? (
                        <>
                          <Loader2 size={16} className="spin" /> Processing...
                        </>
                      ) : (
                        "Register + Apply Leave"
                      )}
                    </button>
                    <button
                      type="button"
                      className="quick-prompt-btn"
                      onClick={handleCancelRegistration}
                      disabled={registrationStatus === "registering"}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}

          {registrationStatus === "success" && registrationResult && (
            <div className="ticket-result ticket-result--success">
              <CheckCircle2 size={18} />
              <div>
                <div className="ticket-result__title">Event registration successful</div>
                <div>Event action ID: {registrationResult.eventActionId}</div>
                <div>Leave request submitted</div>
                <div>Leave action ID: {registrationResult.leaveActionId}</div>
                <div>Faculty approval: Pending</div>
                <div>All actions are recorded and auditable.</div>
              </div>
            </div>
          )}

          {registrationStatus === "error" && registrationError && (
            <div className="ticket-result ticket-result--error">
              <AlertTriangle size={18} />
              <div>
                <div>{registrationError}</div>
                <button
                  type="button"
                  className="quick-prompt-btn"
                  onClick={handleCancelRegistration}
                >
                  Start over
                </button>
              </div>
            </div>
          )}
        </section>

        <section className="glass-card actions-panel">
          <div className="panel-heading">
            <Wrench size={18} />
            <h2>Report Maintenance</h2>
          </div>

          <form className="maintenance-form" onSubmit={handleCreateTicket}>
            <div className="form-field">
              <label htmlFor="location">Location</label>
              <input
                id="location"
                type="text"
                placeholder="e.g. Room 302"
                value={ticketForm.location}
                onChange={(e) =>
                  setTicketForm((f) => ({ ...f, location: e.target.value }))
                }
              />
            </div>

            <div className="form-field">
              <label htmlFor="issue">Issue</label>
              <input
                id="issue"
                type="text"
                placeholder="Describe the issue"
                value={ticketForm.issue}
                onChange={(e) => setTicketForm((f) => ({ ...f, issue: e.target.value }))}
              />
            </div>

            <div className="form-field">
              <label htmlFor="priority">Priority</label>
              <select
                id="priority"
                value={ticketForm.priority}
                onChange={(e) =>
                  setTicketForm((f) => ({ ...f, priority: e.target.value }))
                }
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>

            <button type="submit" className="create-ticket-btn" disabled={ticketStatus === "loading"}>
              {ticketStatus === "loading" ? (
                <>
                  <Loader2 size={16} className="spin" /> Creating...
                </>
              ) : (
                "Create Ticket"
              )}
            </button>
          </form>

          {ticketStatus === "success" && ticketResult && (
            <div className="ticket-result ticket-result--success">
              <CheckCircle2 size={18} />
              <div>
                <div className="ticket-result__title">Ticket created</div>
                <div className="ticket-result__id">
                  Action ID: {ticketResult.action_id || ticketResult.id || "N/A"}
                </div>
              </div>
            </div>
          )}

          {ticketStatus === "error" && ticketError && (
            <div className="ticket-result ticket-result--error">
              <AlertTriangle size={18} />
              <div>{ticketError}</div>
            </div>
          )}
        </section>
        <DecisionDemo />
      </main>
    </div>
  );
}