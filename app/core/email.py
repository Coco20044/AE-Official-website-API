import resend
from app.core.config import settings

async def send_email(to_email:str,subject:str,html_content:str):
    resend.api_key = settings.RESEND_API_KEY
    email_data = {
        "from":settings.EMAIL_FROM,
        "to":[to_email],
        "subject":subject,
        "html":html_content
    }
    response=await resend.Emails.send_async(email_data)
    return response