alter table "public"."users" add column "company" text;

alter table "public"."users" add column "company_size" text;

alter table "public"."users" add column "industry" text;

alter table "public"."users" add column "name" text;

alter table "public"."users" add column "role" text;

set check_function_bodies = off;

CREATE OR REPLACE FUNCTION public.join_waitlist(company text, company_size text, industry text, role text, name text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$begin
  update users set company = join_waitlist.company, role = join_waitlist.role, industry = join_waitlist.industry, company_size = join_waitlist.company_size, name = join_waitlist.name where users.auth_user_id = auth.uid();
end;$function$
;

CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$begin
    if exists(select 1 from public.users where email = lower(new.email)) then
        update public.users set auth_user_id = new.id where email = lower(new.email);
    end if;
    insert into public.users (email, auth_user_id, enable) values (lower(new.email), new.id, false);
    return new;
end;$function$
;


