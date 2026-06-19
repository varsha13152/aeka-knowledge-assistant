'use client';

/**
 * Syncs Clerk's session token into the API client module.
 *
 * This component runs as a child of ClerkProvider and keeps the
 * api.ts module's token in sync with Clerk's session state.
 * It renders nothing — it's a side-effect-only component.
 */

import { useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { setSessionToken } from '@/lib/api';

export function TokenProvider({ children }: { children: React.ReactNode }) {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    if (!isSignedIn) {
      setSessionToken(null);
      return;
    }

    // Get token immediately
    getToken().then(setSessionToken);

    // Refresh token periodically (every 50s — Clerk tokens last ~60s)
    const interval = setInterval(async () => {
      const token = await getToken();
      setSessionToken(token);
    }, 50_000);

    return () => clearInterval(interval);
  }, [getToken, isSignedIn]);

  return <>{children}</>;
}
