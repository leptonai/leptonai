export interface User {
  id: string;
  email: string;
  enable: boolean;
  company?: string;
  companySize?: string;
  industry?: string;
  role?: string;
  name?: string | null;
}
