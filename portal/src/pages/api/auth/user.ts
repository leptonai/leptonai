import { cors } from "@/utils/cors";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";

const user: NextApiWithSupabaseHandler = async (_, res, supabase, session) => {
  const { data, error } = await supabase
    .from("users")
    .select("id, email, enable, name")
    .eq("email", session.user.email)
    .single();

  if (error) {
    return res.status(500).json({ error: error.message });
  }

  if (!data) {
    return res.status(404).json({ error: "User not found" });
  }

  const user = {
    last_sign_in_at: session.user.last_sign_in_at,
    phone: session.user.phone,
    metadata: session.user.user_metadata,
    role: session.user.role,
    ...data,
  };

  return res.json(user);
};

export default cors(serverClientWithAuthorized(user));
