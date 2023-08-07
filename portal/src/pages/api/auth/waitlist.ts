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

  const { data, error } = await supabase.rpc("join_waitlist", {
    name: body.name,
    company: body.company,
    role: body.role,
    company_size: body.company_size || "",
    industry: body.industry || "",
    work_email: body.work_email || "",
  });

  if (error) {
    return res.status(500).json({ error: error.message });
  }

  return res.json(data);
};

export default cors(serverClientWithAuthorized(waitlist));
