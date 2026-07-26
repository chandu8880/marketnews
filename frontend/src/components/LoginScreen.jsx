import { useEffect, useRef, useState } from "react";
import { requestOtp, verifyOtp } from "../api";

const PHONE = "9182813062";
const OTP_TTL_SECONDS = 120;

export default function LoginScreen({ onLogin }) {
  const [stage, setStage] = useState("phone"); // "phone" | "otp"
  const [devOtp, setDevOtp] = useState(null);
  const [code, setCode] = useState("");
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => clearInterval(timerRef.current);
  }, []);

  function startCountdown() {
    clearInterval(timerRef.current);
    setSecondsLeft(OTP_TTL_SECONDS);
    timerRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(timerRef.current);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  }

  function handleSendOtp() {
    setSending(true);
    setError(null);
    requestOtp(PHONE)
      .then((res) => {
        if (!res.ok) {
          setError(res.error || "Could not send OTP.");
          return;
        }
        setDevOtp(res.dev_otp);
        setStage("otp");
        setCode("");
        startCountdown();
      })
      .catch((e) => setError(e.message || "Could not send OTP."))
      .finally(() => setSending(false));
  }

  function handleVerify(e) {
    e.preventDefault();
    setVerifying(true);
    setError(null);
    verifyOtp(PHONE, code)
      .then((res) => {
        if (!res.ok) {
          setError(res.error || "Verification failed.");
          return;
        }
        onLogin(PHONE);
      })
      .catch((e) => setError(e.message || "Verification failed."))
      .finally(() => setVerifying(false));
  }

  const expired = stage === "otp" && secondsLeft === 0;
  const mins = String(Math.floor(secondsLeft / 60)).padStart(1, "0");
  const secs = String(secondsLeft % 60).padStart(2, "0");

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-logo">📈</div>
        <h1 className="login-title">MarketPulse</h1>
        <p className="login-subtitle">Sign in to continue</p>

        <div className="login-field">
          <label className="login-label">Phone number</label>
          <input className="login-input" type="tel" value={PHONE} readOnly disabled />
        </div>

        {stage === "phone" && (
          <button className="login-btn" onClick={handleSendOtp} disabled={sending}>
            {sending ? "Sending…" : "Send OTP"}
          </button>
        )}

        {stage === "otp" && (
          <form onSubmit={handleVerify} className="login-otp-form">
            <div className="login-dev-otp">
              <div className="login-dev-otp-label">DEV MODE — your OTP (not sent via real SMS)</div>
              <div className="login-dev-otp-code">{devOtp}</div>
            </div>

            <div className="login-field">
              <label className="login-label">
                Enter OTP{" "}
                <span className={expired ? "login-timer-expired" : "login-timer"}>
                  {expired ? "expired" : `valid ${mins}:${secs}`}
                </span>
              </label>
              <input
                className="login-input"
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="6-digit code"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                autoFocus
              />
            </div>

            <button className="login-btn" type="submit" disabled={verifying || expired || code.length !== 6}>
              {verifying ? "Verifying…" : "Verify & Login"}
            </button>

            <button type="button" className="login-resend-btn" onClick={handleSendOtp} disabled={sending}>
              {expired ? "Resend OTP" : "Send a new OTP"}
            </button>
          </form>
        )}

        {error && <div className="login-error">{error}</div>}
      </div>
    </div>
  );
}
