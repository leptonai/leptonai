import { createClient } from "@supabase/supabase-js";

export const supabaseClient = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_ANON_KEY!,
  {
    auth: {
      persistSession: false,
    },
  },
);

// Caution: this is the admin supabase client, should not expose it directly
export const supabaseAdminClient = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SECRET_KEY!,
  {
    auth: {
      persistSession: false,
    },
  },
);
