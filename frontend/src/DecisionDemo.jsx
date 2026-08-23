import { useState } from "react";
import { ShieldCheck } from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export default function DecisionDemo() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const form = e.target;

    const payload = {
      student_id: Number(form.student_id.value),
      intent: form.intent.value,
      event_name: form.event_name.value,
      event_time: form.event_time.value,
      subject: form.subject.value,
      planned_missed_classes: Number(form.planned_missed_classes.value),
    };

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/decision/campus`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok || data.success === false) {
        throw new Error(
          data.detail || data.message || "Decision analysis failed."
        );
      }
      setResult(data);
    } catch (err) {
      console.error(err);
      setResult({ error: err.message || "Failed to call decision API." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="glass-card decision-panel">
      <div className="panel-heading">
        <ShieldCheck size={18} />
        <div>
          <h2>Campus Decision Engine</h2>
          <p className="decision-panel__subtitle">
            Review attendance impact before submitting an event leave request.
          </p>
        </div>
      </div>

      <form className="decision-form" onSubmit={handleSubmit}>
        <label className="decision-field">
          Student ID
          <input
            name="student_id"
            defaultValue="1"
            type="number"
          />
        </label>

        <label className="decision-field decision-field--wide">
          Intent
          <textarea
            name="intent"
            defaultValue="I want to attend the AI Innovation Workshop tomorrow and I am okay missing one DBMS class if it is safe."
            rows={3}
          />
        </label>

        <label className="decision-field">
          Event name
          <input
            name="event_name"
            defaultValue="AI Innovation Workshop"
          />
        </label>

        <label className="decision-field">
          Event time
          <input
            name="event_time"
            defaultValue="2026-08-23T14:00:00"
            type="datetime-local"
          />
        </label>

        <label className="decision-field">
          Subject
          <input
            name="subject"
            defaultValue="Database Management Systems"
          />
        </label>

        <label className="decision-field">
          Planned missed classes
          <input
            name="planned_missed_classes"
            defaultValue="1"
            type="number"
            min="0"
            max="10"
          />
        </label>

        <button
          type="submit"
          className="decision-submit"
          disabled={loading}
        >
          {loading ? "Analyzing..." : "Analyze Decision"}
        </button>
      </form>

      {result && (
        <div className={`decision-result ${result.error ? "decision-result--error" : ""}`}>
          <div className="decision-result__header">
            <div>
              <div className="decision-result__eyebrow">Analysis result</div>
              <h3>Decision</h3>
            </div>
            {!result.error && (
              <span
                className={`status-badge status-badge--${
                  result.data?.decision?.risk_level === "low" ? "safe" : "attention"
                }`}
              >
                {result.data?.decision?.risk_level || "Unknown"} risk
              </span>
            )}
          </div>

          {result.error ? (
            <p className="decision-result__error">{result.error}</p>
          ) : (
            <>
              <div className="decision-result__meta">
                <span>Agent: {result.agent}</span>
                <span>
                  Eligibility: {result.data?.decision?.eligible_for_event_leave ? "Approved" : "Not approved"}
                </span>
              </div>
              <p className="decision-result__recommendation">
                {result.data?.decision?.recommendation}
              </p>

              <div className="decision-impact">
                <div>
                  <span>Current</span>
                  <strong>{result.data?.attendance_impact?.current_percentage}%</strong>
                </div>
                <div>
                  <span>Projected</span>
                  <strong>{result.data?.attendance_impact?.projected_percentage}%</strong>
                </div>
                <div>
                  <span>Minimum required</span>
                  <strong>{result.data?.attendance_impact?.minimum_required_percentage}%</strong>
                </div>
              </div>

              <div className="decision-policy">
                <strong>Policy evidence</strong>
                <ul>
                  {result.data?.policy_evidence?.map((p, i) => (
                    <li key={i}>
                      {p.source} · Section {p.section}
                    </li>
                  ))}
                </ul>
              </div>

            </>
          )}
        </div>
      )}
    </section>
  );
}