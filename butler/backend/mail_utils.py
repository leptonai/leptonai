from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Asm
import database
import os
import dotenv

dotenv.load_dotenv()
send_grid_api_key = os.environ.get("SEND_GRID_KEY")


def send_welcome(destination):
    """
    Input:
        detination : a tuple contains two elements, eg:
            ('yuze.bob.ma@gmail.com', 'Yuze Ma')
    """
    # from address we pass to our Mail object, edit with your name
    FROM_EMAIL = "uz@lepton.ai"

    # update to your dynamic template id from the UI
    TEMPLATE_ID = "d-32c4d10c26c34ee5bafb2bb240dd7860"

    TO_EMAILS = [destination]

    message = Mail(from_email=FROM_EMAIL, to_emails=TO_EMAILS)
    # pass custom values for our HTML placeholders
    message.dynamic_template_data = {"user_name": destination[1]}
    message.template_id = TEMPLATE_ID
    asm = Asm(group_id=21845)
    message.asm = asm

    sg = SendGridAPIClient(send_grid_api_key)
    response = sg.send(message)

    SQL = '''INSERT INTO user_mail_record (mail, subject, status_code) VALUES ('{}', '{}', '{}');
    '''.format(destination[0], "Welcome", response.status_code)

    database.execute_sql(SQL)
    print("mail sent to {} with status code {}".format(destination[0], response.status_code))

    return response.status_code


def send_one_on_one_invitation(destination):
    """
    Input:
        detination : a tuple contains two elements, eg:
            ('yuze.bob.ma@gmail.com', 'Yuze Ma')
    """
    # from address we pass to our Mail object, edit with your name
    FROM_EMAIL = "uz@lepton.ai"

    # update to your dynamic template id from the UI
    TEMPLATE_ID = "d-c0d2f09f5c0143d6ad9e932376f6a9eb"

    TO_EMAILS = [destination]

    message = Mail(from_email=FROM_EMAIL, to_emails=TO_EMAILS)
    # pass custom values for our HTML placeholders
    message.dynamic_template_data = {"user_name": destination[1]}
    message.template_id = TEMPLATE_ID
    asm = Asm(group_id=21845)
    message.asm = asm

    sg = SendGridAPIClient(send_grid_api_key)
    response = sg.send(message)

    SQL = '''INSERT INTO user_mail_record (mail, subject, status_code) VALUES ('{}', '{}', '{}');
    '''.format(destination[0], "One-One-Invitation", response.status_code)

    database.execute_sql(SQL)
    print("mail sent to {} with status code {}".format(destination[0], response.status_code))
    return response.status_code
