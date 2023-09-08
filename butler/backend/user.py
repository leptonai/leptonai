import database
import pandas as pd
import uuid


def get_user_by_email(email: str) -> dict:
    db_connection = database.get_supabase_connection()
    query = "SELECT * FROM users WHERE email = '{}'".format(email)
    df = pd.read_sql(query, db_connection)
    db_connection.close()
    return df.iloc[0]


def activate_user(email):
    user_id = get_user_by_email(email)["id"]
    query = "UPDATE users SET enable = TRUE WHERE id = '{}'".format(user_id)
    database.execute_sql(query)
    return get_user_by_email(email)


def add_user(email):
    # Check if user exists
    db_connection = database.get_supabase_connection()
    query = "SELECT * FROM public.users WHERE email = '{}'".format(email)
    df = pd.read_sql(query, db_connection)
    db_connection.close()
    # If user exists, return 
    if len(df) > 0:
        activate_user(email)
        print("User {} already exists, successfully activated".format(email))
        return get_user_by_email(email)
    # If user does not exist, add user
    user_id = str(uuid.uuid1())
    user_email = email
    enabled = True
    query = "INSERT INTO users (id, email, enable) VALUES ('{}', '{}', '{}')"\
        .format(user_id, user_email, enabled)
    database.execute_sql(query)
    print("User {} successfully added".format(email))
    return get_user_by_email(email)
