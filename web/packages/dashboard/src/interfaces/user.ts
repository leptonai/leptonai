import { UserMetadata } from "@supabase/supabase-js";

export interface WaitlistEntry {
  company: string;
  companySize: string;
  industry: string;
  role: string;
  name: string;
  workEmail: string;
}

export interface User {
  id: string;
  email: string;
  enable: boolean;
  name?: string | null;
  last_sign_in_at?: string;
  phone?: string;
  role?: string;
  metadata?: UserMetadata;
}
