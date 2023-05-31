import { Injectable } from "injection-js";
import { createClient, Session } from "@supabase/supabase-js";
import { Database } from "@lepton-dashboard/interfaces/database";
import { BehaviorSubject } from "rxjs";

/**
 * Must be instantiated outside AuthService
 */
const client = createClient<Database>(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_KEY
);

@Injectable()
export class AuthService {
  private session$ = new BehaviorSubject<Session | null>(null);
  private ready$ = new BehaviorSubject<boolean>(false);
  private authStateSubscription: {
    unsubscribe: () => void;
  } | null = null;

  readonly client = client;

  constructor() {
    this.client.auth.getSession().then(({ data: { session } }) => {
      this.session$.next(session);
      this.ready$.next(true);
    });

    const {
      data: { subscription },
    } = this.client.auth.onAuthStateChange((_event, session) => {
      this.session$.next(session);
    });

    this.authStateSubscription = subscription;
  }

  ready() {
    return this.ready$.asObservable();
  }

  getToken() {
    return this.session$.value?.access_token || null;
  }

  getUser() {
    return this.session$.value?.user || null;
  }

  logout() {
    return this.client.auth.signOut().then(() => {
      this.session$.next(null);
    });
  }

  destroy() {
    this.authStateSubscription?.unsubscribe();
  }
}
