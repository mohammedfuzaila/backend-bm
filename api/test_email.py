from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse

def test_email_view(request):
    try:
        subject = 'Test Email from BachMates'
        message = 'If you receive this, SMTP is working!'
        recipient_list = ['anaikarmohammedfuzail57@gmail.com'] # Test with the sender's email itself
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        return HttpResponse("Email sent successfully!")
    except Exception as e:
        return HttpResponse(f"Failed to send email: {str(e)}")
