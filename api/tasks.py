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
            
            agent_html = f"""
            <html><body style='font-family:sans-serif;padding:20px;'>
                <h2>Is the Work Completed?</h2>
                <p>Hello {booking.assigned_agent.name},</p>
                <p>You accepted <strong>Booking #{booking.id} ({booking.service.title})</strong> about 5 minutes ago.</p>
                <p>If you have finished the work, please click the button below to mark it as complete so the customer can proceed with payment.</p>
                <div style='margin: 25px 0;'>
                    <a href='{complete_link}' style='background:#5c62f1;color:white;padding:12px 25px;text-decoration:none;border-radius:8px;font-weight:bold;'>Mark as Completed</a>
                </div>
                <p>Thank you!</p>
            </body></html>
            """
            
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = settings.BREVO_API_KEY
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
            
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": agent_email}],
                html_content=agent_html,
                subject=subject,
                sender={"email": settings.DEFAULT_FROM_EMAIL, "name": "BachMates"}
            )
            api_instance.send_transac_email(send_smtp_email)
            print(f"Follow-up email sent to {agent_email} for booking {booking.id}.")
    except Booking.DoesNotExist:
        print(f"Booking {booking_id} not found for follow-up.")
    except Exception as e:
        print(f"Error in follow-up task: {e}")

def schedule_followup_email(booking_id, agent_id, delay_seconds=300):
    """
    Schedules a follow-up email to be sent after `delay_seconds`.
    Default is 300 seconds (5 minutes).
    """
    timer = threading.Timer(delay_seconds, send_followup_email, args=[booking_id, agent_id])
    timer.start()
    print(f"Scheduled follow-up email for booking {booking_id} in {delay_seconds} seconds.")
