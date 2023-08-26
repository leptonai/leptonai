create table "public"."compute_hourly" (
    "workspace_id" text not null default ''::text,
    "deployment_name" text not null default ''::text,
    "shape" text not null default ''::text,
    "end_time" timestamp with time zone not null default now(),
    "usage" bigint not null,
    "batch_id" uuid not null,
    "stripe_usage_record_id" text default 'NULL'::text,
    "id" uuid not null default gen_random_uuid()
);

alter table "public"."compute_hourly" enable row level security;

create table "public"."storage_hourly" (
    "workspace_id" text not null,
    "storage_id" text not null,
    "size_bytes" bigint,
    "end_time" timestamp with time zone not null,
    "batch_id" uuid,
    "id" uuid not null default gen_random_uuid(),
    "size_gb" integer,
    "stripe_usage_record_id" text default 'NULL'::text
);

alter table "public"."storage_hourly" enable row level security;

CREATE TRIGGER report_stripe_compute AFTER INSERT ON public.compute_hourly FOR EACH ROW EXECUTE FUNCTION supabase_functions.http_request('https://portal.lepton.ai/api/billing/report-compute', 'POST', '{"Content-type":"application/json"}', '{"LEPTON_API_SECRET":"LEPTON_API_SECRET"}', '60000');

CREATE TRIGGER report_stripe_storage AFTER INSERT ON public.storage_hourly FOR EACH ROW EXECUTE FUNCTION supabase_functions.http_request('https://portal.lepton.ai/api/billing/report-storage', 'POST', '{"Content-type":"application/json"}', '{"LEPTON_API_SECRET":"LEPTON_API_SECRET"}', '60000');
