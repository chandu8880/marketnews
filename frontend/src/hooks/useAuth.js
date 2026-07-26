import { useCallback, useEffect, useState } from "react";
import { checkSession, logoutSession } from "../api";

export function useAuth() {
  const [email, setEmail] = useState(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;
    checkSession()
      .then((res) => {
        if (!cancelled && res.valid) setEmail(res.email);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // The session cookie is set by the server (HttpOnly - this page never
  // sees or stores the token itself); login() just records who's signed in
  // for the UI.
  const login = useCallback((loggedInEmail) => {
    setEmail(loggedInEmail);
  }, []);

  const logout = useCallback(() => {
    logoutSession().catch(() => {});
    setEmail(null);
  }, []);

  return {
    isLoggedIn: !!email,
    checking,
    email,
    login,
    logout,
  };
}
