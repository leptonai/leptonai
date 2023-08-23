create type "public"."tier" as enum ('Basic', 'Standard', 'Enterprise');

alter table "public"."workspaces" rename type to tier;

alter table "public"."workspaces" alter column "tier" type tier using tier::tier;
