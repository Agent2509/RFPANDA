// ============================================================================
// RFPANDA — Supabase Client Helper for Edge Functions
// ============================================================================

import {
  createClient,
  SupabaseClient,
} from "https://esm.sh/@supabase/supabase-js@2.39.8";

/**
 * Creates a Supabase client configured with the service_role key for admin operations
 * (e.g. storage downloads, vector insertions, cross-tenant status updates).
 */
export function getServiceRoleClient(): SupabaseClient {
  const supabaseUrl = Deno.env.get("SUPABASE_URL") ||
    Deno.env.get("SUPABASE_PROJECT_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

  if (!supabaseUrl) {
    throw new Error("Missing environment variable: SUPABASE_URL");
  }
  if (!serviceKey) {
    throw new Error("Missing environment variable: SUPABASE_SERVICE_ROLE_KEY");
  }

  return createClient(supabaseUrl, serviceKey, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  });
}

/**
 * Creates a Supabase client scoped to an authenticated user's JWT
 * for enforcing Row Level Security (RLS) during user-initiated requests.
 */
export function getUserClient(authHeaderOrToken: string): SupabaseClient {
  const supabaseUrl = Deno.env.get("SUPABASE_URL") ||
    Deno.env.get("SUPABASE_PROJECT_URL");
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") ||
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

  if (!supabaseUrl) {
    throw new Error("Missing environment variable: SUPABASE_URL");
  }
  if (!anonKey) {
    throw new Error("Missing environment variable: SUPABASE_ANON_KEY");
  }

  const token = authHeaderOrToken.startsWith("Bearer ")
    ? authHeaderOrToken.slice(7).trim()
    : authHeaderOrToken.trim();

  return createClient(supabaseUrl, anonKey, {
    global: {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  });
}
