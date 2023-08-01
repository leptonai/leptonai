import dotenv
dotenv.load_dotenv()

import psycopg2
import pandas as pd
import os

def get_supabase_connection():
    try:
        connection = psycopg2.connect(
            user=os.getenv("PSQL_USER"),
            password=os.getenv("PSQL_PASSWORD"),
            host=os.getenv("PSQL_HOST"),
            port=os.getenv("PSQL_PORT"),
            database=os.getenv("PSQL_DATABASE"),
        )
        return connection

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL:", error)

def execute_sql(query):
    db_connection = get_supabase_connection()
    db_cursor = db_connection.cursor()
    db_cursor.execute(query)
    db_connection.commit()
    
    db_cursor.close()
    db_connection.close()

def get_user_by_email(email:str) -> dict : 
    db_connection = get_supabase_connection()
    query = "SELECT * FROM users WHERE email = '{}'".format(email)
    df = pd.read_sql(query, db_connection)
    db_connection.close()
    return df.iloc[0]

def get_workspcae_by_display_name(workspace_display_name:str) -> dict : 
    db_connection = get_supabase_connection()
    query = "SELECT * FROM workspaces WHERE display_name = '{}'".format(workspace_display_name)
    df = pd.read_sql(query, db_connection)
    db_connection.close()
    return df.iloc[0]

def get_max_id_for_user_workspace():
    db_con = get_supabase_connection()
    db_cursor = db_con.cursor()
    query = "SELECT MAX(id) FROM user_workspace"
    db_cursor.execute(query)

    results = db_cursor.fetchall()[0][0]
    db_con.commit()
    db_cursor.close()
    db_con.close()
    return results

def get_workspace_users(workspace_id:str):
    db_connection = get_supabase_connection()
    query = "SELECT * FROM user_workspace WHERE workspace_id = '{}'".format(workspace_id)
    df = pd.read_sql(query, db_connection)
    db_connection.close()
    users = set(df['user_id'].tolist())
    return users