export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Database {
  graphql_public: {
    Tables: {
      [_ in never]: never;
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      graphql: {
        Args: {
          operationName?: string;
          query?: string;
          variables?: Json;
          extensions?: Json;
        };
        Returns: Json;
      };
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
  public: {
    Tables: {
      compute_hourly: {
        Row: {
          batch_id: string;
          deployment_name: string;
          end_time: string;
          id: string;
          shape: string;
          stripe_usage_record_id: string | null;
          usage: number;
          workspace_id: string;
        };
        Insert: {
          batch_id: string;
          deployment_name?: string;
          end_time?: string;
          id?: string;
          shape?: string;
          stripe_usage_record_id?: string | null;
          usage: number;
          workspace_id?: string;
        };
        Update: {
          batch_id?: string;
          deployment_name?: string;
          end_time?: string;
          id?: string;
          shape?: string;
          stripe_usage_record_id?: string | null;
          usage?: number;
          workspace_id?: string;
        };
        Relationships: [];
      };
      storage_hourly: {
        Row: {
          batch_id: string | null;
          end_time: string;
          id: string;
          size_bytes: number | null;
          size_gb: number | null;
          storage_id: string;
          stripe_usage_record_id: string | null;
          workspace_id: string;
        };
        Insert: {
          batch_id?: string | null;
          end_time: string;
          id?: string;
          size_bytes?: number | null;
          size_gb?: number | null;
          storage_id: string;
          stripe_usage_record_id?: string | null;
          workspace_id: string;
        };
        Update: {
          batch_id?: string | null;
          end_time?: string;
          id?: string;
          size_bytes?: number | null;
          size_gb?: number | null;
          storage_id?: string;
          stripe_usage_record_id?: string | null;
          workspace_id?: string;
        };
        Relationships: [];
      };
      user_workspace: {
        Row: {
          id: number;
          token: string;
          user_id: string;
          workspace_id: string;
        };
        Insert: {
          id?: number;
          token: string;
          user_id: string;
          workspace_id: string;
        };
        Update: {
          id?: number;
          token?: string;
          user_id?: string;
          workspace_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "user_workspace_user_id_fkey";
            columns: ["user_id"];
            referencedRelation: "users";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "user_workspace_workspace_id_fkey";
            columns: ["workspace_id"];
            referencedRelation: "workspaces";
            referencedColumns: ["id"];
          }
        ];
      };
      users: {
        Row: {
          auth_user_id: string | null;
          company: string | null;
          company_size: string | null;
          created_at: string | null;
          email: string;
          enable: boolean;
          id: string;
          industry: string | null;
          name: string | null;
          role: string | null;
          url: string;
          work_email: string | null;
        };
        Insert: {
          auth_user_id?: string | null;
          company?: string | null;
          company_size?: string | null;
          created_at?: string | null;
          email: string;
          enable?: boolean;
          id?: string;
          industry?: string | null;
          name?: string | null;
          role?: string | null;
          url: string;
          work_email?: string | null;
        };
        Update: {
          auth_user_id?: string | null;
          company?: string | null;
          company_size?: string | null;
          created_at?: string | null;
          email?: string;
          enable?: boolean;
          id?: string;
          industry?: string | null;
          name?: string | null;
          role?: string | null;
          url?: string;
          work_email?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "users_auth_user_id_fkey";
            columns: ["auth_user_id"];
            referencedRelation: "users";
            referencedColumns: ["id"];
          }
        ];
      };
      workspaces: {
        Row: {
          chargeable: boolean;
          consumer_id: string | null;
          coupon_id: string | null;
          created_at: string | null;
          display_name: string | null;
          id: string;
          last_billable_usage_timestamp: string | null;
          payment_method_attached: boolean;
          status: string | null;
          subscription_id: string | null;
          tier: Database["public"]["Enums"]["tier"] | null;
          url: string | null;
        };
        Insert: {
          chargeable: boolean;
          consumer_id?: string | null;
          coupon_id?: string | null;
          created_at?: string | null;
          display_name?: string | null;
          id: string;
          last_billable_usage_timestamp?: string | null;
          payment_method_attached?: boolean;
          status?: string | null;
          subscription_id?: string | null;
          tier?: Database["public"]["Enums"]["tier"] | null;
          url?: string | null;
        };
        Update: {
          chargeable?: boolean;
          consumer_id?: string | null;
          coupon_id?: string | null;
          created_at?: string | null;
          display_name?: string | null;
          id?: string;
          last_billable_usage_timestamp?: string | null;
          payment_method_attached?: boolean;
          status?: string | null;
          subscription_id?: string | null;
          tier?: Database["public"]["Enums"]["tier"] | null;
          url?: string | null;
        };
        Relationships: [];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      join_waitlist: {
        Args: {
          company: string;
          company_size: string;
          industry: string;
          role: string;
          name: string;
          work_email: string;
        };
        Returns: undefined;
      };
    };
    Enums: {
      tier: "Basic" | "Standard" | "Enterprise";
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
  storage: {
    Tables: {
      buckets: {
        Row: {
          allowed_mime_types: string[] | null;
          avif_autodetection: boolean | null;
          created_at: string | null;
          file_size_limit: number | null;
          id: string;
          name: string;
          owner: string | null;
          public: boolean | null;
          updated_at: string | null;
        };
        Insert: {
          allowed_mime_types?: string[] | null;
          avif_autodetection?: boolean | null;
          created_at?: string | null;
          file_size_limit?: number | null;
          id: string;
          name: string;
          owner?: string | null;
          public?: boolean | null;
          updated_at?: string | null;
        };
        Update: {
          allowed_mime_types?: string[] | null;
          avif_autodetection?: boolean | null;
          created_at?: string | null;
          file_size_limit?: number | null;
          id?: string;
          name?: string;
          owner?: string | null;
          public?: boolean | null;
          updated_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "buckets_owner_fkey";
            columns: ["owner"];
            referencedRelation: "users";
            referencedColumns: ["id"];
          }
        ];
      };
      migrations: {
        Row: {
          executed_at: string | null;
          hash: string;
          id: number;
          name: string;
        };
        Insert: {
          executed_at?: string | null;
          hash: string;
          id: number;
          name: string;
        };
        Update: {
          executed_at?: string | null;
          hash?: string;
          id?: number;
          name?: string;
        };
        Relationships: [];
      };
      objects: {
        Row: {
          bucket_id: string | null;
          created_at: string | null;
          id: string;
          last_accessed_at: string | null;
          metadata: Json | null;
          name: string | null;
          owner: string | null;
          path_tokens: string[] | null;
          updated_at: string | null;
          version: string | null;
        };
        Insert: {
          bucket_id?: string | null;
          created_at?: string | null;
          id?: string;
          last_accessed_at?: string | null;
          metadata?: Json | null;
          name?: string | null;
          owner?: string | null;
          path_tokens?: string[] | null;
          updated_at?: string | null;
          version?: string | null;
        };
        Update: {
          bucket_id?: string | null;
          created_at?: string | null;
          id?: string;
          last_accessed_at?: string | null;
          metadata?: Json | null;
          name?: string | null;
          owner?: string | null;
          path_tokens?: string[] | null;
          updated_at?: string | null;
          version?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "objects_bucketId_fkey";
            columns: ["bucket_id"];
            referencedRelation: "buckets";
            referencedColumns: ["id"];
          }
        ];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      can_insert_object: {
        Args: {
          bucketid: string;
          name: string;
          owner: string;
          metadata: Json;
        };
        Returns: undefined;
      };
      extension: {
        Args: {
          name: string;
        };
        Returns: string;
      };
      filename: {
        Args: {
          name: string;
        };
        Returns: string;
      };
      foldername: {
        Args: {
          name: string;
        };
        Returns: unknown;
      };
      get_size_by_bucket: {
        Args: Record<PropertyKey, never>;
        Returns: {
          size: number;
          bucket_id: string;
        }[];
      };
      search: {
        Args: {
          prefix: string;
          bucketname: string;
          limits?: number;
          levels?: number;
          offsets?: number;
          search?: string;
          sortcolumn?: string;
          sortorder?: string;
        };
        Returns: {
          name: string;
          id: string;
          updated_at: string;
          created_at: string;
          last_accessed_at: string;
          metadata: Json;
        }[];
      };
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
}
