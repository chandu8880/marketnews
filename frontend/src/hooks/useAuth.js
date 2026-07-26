import { useCallback, useEffect, useState } from "react";
import { checkSession, logoutSession } from "../api";

export function useAuth() {
  const [phone, setPhone] = useState(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;
    checkSession()
      .then((res) => {
        if (!cancelled && res.valid) setPhone(res.phone);
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
  const login = useCallback((loggedInPhone) => {
    setPhone(loggedInPhone);
  }, []);

  const logout = useCallback(() => {
    logoutSession().catch(() => {});
    setPhone(null);
  }, []);

  return {
    isLoggedIn: !!phone,
    checking,
    phone,
    login,
    logout,
  };
}
