-- fill existing rows with chargeable = false
alter table "public"."workspaces" add column "chargeable" boolean not null default false;
-- drop default value to ensure that the column is not null in the future
alter table "public"."workspaces" alter column  "chargeable" drop default;
