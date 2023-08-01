import { cors } from "@/utils/cors";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";

const waitlist: NextApiWithSupabaseHandler = async (req, res, supabase) => {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }
  const body = req.body;

  const { data, error } = await supabase.rpc("join_waitlist", body);

  if (error) {
    return res.status(500).json({ error: error.message });
  }

  return res.json(data);
};

export default cors(serverClientWithAuthorized(waitlist));
