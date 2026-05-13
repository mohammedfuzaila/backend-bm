import threading
from django.conf import settings
from .models import Booking
import sib_api_v3_sdk

def send_followup_email(booking_id, agent_id):
    """
    Function to be executed after the delay.
    Checks if the booking is still IN_PROGRESS and sends a follow-up email.
    """
    try:
        booking = Booking.objects.get(id=booking_id)
        # Check if booking is still ACCEPTED and assigned to this agent
        if booking.status == 'ACCEPTED' and booking.assigned_agent and booking.assigned_agent.id == agent_id:
            agent_email = booking.assigned_agent.email
            subject = f"Follow-up: Is the work completed for Booking #{booking.id}?"
            
            # Construct the complete action link
            complete_link = f"{settings.BACKEND_URL}/api/booking/{booking.id}/complete/{agent_id}/"
            
            message = (
                f"Hello {booking.assigned_agent.name},\n\n"
                f"You accepted Booking #{booking.id} ({booking.service.title}) a while ago.\n"
                f"Is the work completed?\n\n"
                f"If yes, please click the link below to mark it as complete:\n"
                f"COMPLETE: {complete_link}\n\n"
                f"Thank you!"
            )
            
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = settings.BREVO_API_KEY
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
            
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": agent_email}],
                html_content=message,
                subject=subject,
                sender={"email": settings.DEFAULT_FROM_EMAIL, "name": "BachMates"}
            )
            api_instance.send_transac_email(send_smtp_email)
            print(f"Follow-up email sent to {agent_email} for booking {booking.id}.")
    except Booking.DoesNotExist:
        print(f"Booking {booking_id} not found for follow-up.")
    except Exception as e:
        print(f"Error in follow-up task: {e}")

def schedule_followup_email(booking_id, agent_id, delay_seconds=420):
    """
    Schedules a follow-up email to be sent after `delay_seconds`.
    Default is 420 seconds (7 minutes).
    """
    timer = threading.Timer(delay_seconds, send_followup_email, args=[booking_id, agent_id])
    timer.start()
    print(f"Scheduled follow-up email for booking {booking_id} in {delay_seconds} seconds.")
