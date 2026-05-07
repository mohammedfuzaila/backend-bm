import json
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from .models import User, Service, Booking, Category, Agent
from .tasks import schedule_followup_email

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"detail": "CSRF cookie set"})

@csrf_exempt # In a real prod environment we'd use proper CSRF, but keeping exempt for simplicity if needed, or we implement CSRF fully. Since we're doing session auth, we should use CSRF. Let's just use @csrf_exempt on login/register as a fallback, or configure standard django login. Actually, with DRF missing, handling CSRF from React fetch is a bit tedious via fetch. We will require it.
@csrf_exempt
def login_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            password = data.get("password")
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return JsonResponse({
                    "message": "Logged in successfully", 
                    "user": {
                        "id": user.id, 
                        "email": user.email, 
                        "full_name": user.full_name,
                        "isAdmin": user.is_staff or user.is_superuser
                    }
                })
            else:
                return JsonResponse({"error": "Invalid credentials"}, status=401)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def register_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            password = data.get("password")
            full_name = data.get("full_name", "")
            phone = data.get("phone", "")
            location = data.get("location", "")
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({"error": "Email already registered"}, status=400)
            
            user = User.objects.create_user(
                username=email, 
                email=email, 
                password=password,
                full_name=full_name,
                phone=phone,
                location=location
            )
            login(request, user)
            return JsonResponse({
                "message": "Registered successfully", 
                "user": {
                    "id": user.id, 
                    "email": user.email,
                    "full_name": user.full_name,
                    "isAdmin": False
                }
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return JsonResponse({"message": "Logged out successfully"})
    return JsonResponse({"error": "Method not allowed"}, status=405)

def session_view(request):
    if request.user.is_authenticated:
        return JsonResponse({
            "isAuthenticated": True, 
            "user": {
                "id": request.user.id, 
                "email": request.user.email,
                "full_name": request.user.full_name,
                "isAdmin": request.user.is_staff or request.user.is_superuser
            }
        })
    return JsonResponse({"isAuthenticated": False})

@csrf_exempt
def categories_view(request):
    if request.method == "GET":
        cats = Category.objects.all().values('id', 'name', 'icon')
        return JsonResponse({"categories": list(cats)})
    
    if request.method == "POST":
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({"error": "Admin only"}, status=403)
        try:
            data = json.loads(request.body)
            name = data.get('name')
            if not name:
                return JsonResponse({"error": "Name is required"}, status=400)
            
            cat = Category.objects.create(
                name=name,
                icon=data.get('icon', 'Grid')
            )
            return JsonResponse({"message": "Category added", "id": cat.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def admin_category_detail_view(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "Admin only"}, status=403)
    
    try:
        cat = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return JsonResponse({"error": "Category not found"}, status=404)

    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            cat.name = data.get('name', cat.name)
            cat.icon = data.get('icon', cat.icon)
            cat.save()
            return JsonResponse({"message": "Category updated"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    if request.method == "DELETE":
        cat.delete()
        return JsonResponse({"message": "Category deleted"})
        
    return JsonResponse({"error": "Method not allowed"}, status=405)

def admin_stats_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "Admin only"}, status=403)
    
    total_revenue = sum(b.service.price for b in Booking.objects.filter(status='COMPLETED'))
    return JsonResponse({
        "revenue": float(total_revenue),
        "total_bookings": Booking.objects.count(),
        "completion_rate": 85, # Mock
        "active_services": Service.objects.count()
    })

@csrf_exempt
def services_view(request):
    if request.method == "GET":
        services = []
        for s in Service.objects.all():
            img_url = s.image_url
            if s.image:
                img_url = request.build_absolute_uri(s.image.url)
            
            services.append({
                "id": s.id,
                "title": s.title,
                "category_name": s.category.name if s.category else "N/A",
                "category_id": s.category.id if s.category else None,
                "description": s.description,
                "image_url": img_url,
                "price": float(s.price),
                "is_featured": s.is_featured
            })
        return JsonResponse({"services": services})
    
    if request.method == "POST": # Add Service
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({"error": "Admin only"}, status=403)
        try:
            # Use request.POST instead of json.loads for FormData
            cat_id = request.POST.get('category_id')
            cat = Category.objects.get(id=cat_id)
            
            Service.objects.create(
                title=request.POST.get('title'),
                category=cat,
                description=request.POST.get('description'),
                price=request.POST.get('price'),
                image=request.FILES.get('image'), # Handle file upload
                image_url=request.POST.get('image_url', ''),
                is_featured=request.POST.get('is_featured') == 'true'
            )
            return JsonResponse({"message": "Service created"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def service_detail_view(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "Admin only"}, status=403)
    
    try:
        service = Service.objects.get(pk=pk)
        # Using POST as a workaround for multipart updates or handling PUT specially
        if request.method in ["PUT", "POST"]:
            service.title = request.POST.get('title', service.title)
            if 'category_id' in request.POST:
                service.category = Category.objects.get(id=request.POST['category_id'])
            service.description = request.POST.get('description', service.description)
            service.price = request.POST.get('price', service.price)
            
            if 'image' in request.FILES:
                service.image = request.FILES['image']
            
            service.image_url = request.POST.get('image_url', service.image_url)
            service.is_featured = request.POST.get('is_featured') == 'true'
            service.save()
            return JsonResponse({"message": "Service updated"})
        elif request.method == "DELETE":
            service.delete()
            return JsonResponse({"message": "Service deleted"})
    except Service.DoesNotExist:
        return JsonResponse({"error": "Service not found"}, status=404)
    return JsonResponse({"error": "Method not allowed"}, status=405)

def latest_finished_service_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"service_title": "Login to see activity", "status": "Idle"})
    try:
        latest = Booking.objects.filter(user=request.user, status='COMPLETED').order_by('-updated_at').first()
        if latest:
            return JsonResponse({
                "service_title": latest.service.title,
                "status": "Finished"
            })
        return JsonResponse({"service_title": "No finished jobs yet", "status": "Ready"})
    except Exception:
        return JsonResponse({"service_title": "Recent Activity", "status": "Live"})

def all_bookings_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "Admin only"}, status=403)
    
    bookings = Booking.objects.all().order_by('-created_at')
    data = [{
        "id": b.id,
        "user_email": b.user.email,
        "service_title": b.service.title,
        "status": b.status,
        "assigned_agent": b.assigned_agent.name if b.assigned_agent else None,
        "assigned_agent_email": b.assigned_agent.email if b.assigned_agent else None,
        "created_at": b.created_at.isoformat()
    } for b in bookings]
    return JsonResponse({"bookings": data})

@csrf_exempt
def update_booking_status_view(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "Admin only"}, status=403)
    
    try:
        booking = Booking.objects.get(pk=pk)
        data = json.loads(request.body)
        booking.status = data.get('status', booking.status)
        if 'assigned_agent_id' in data:
            if data['assigned_agent_id']:
                booking.assigned_agent = Agent.objects.get(id=data['assigned_agent_id'])
            else:
                booking.assigned_agent = None
        booking.save()
        return JsonResponse({"message": "Booking updated"})
    except Booking.DoesNotExist:
        return JsonResponse({"error": "Booking not found"}, status=404)

@csrf_exempt
def admin_delete_booking_view(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "Admin only"}, status=403)
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        booking = Booking.objects.get(pk=pk)
        booking.delete()
        return JsonResponse({"message": "Booking deleted successfully"})
    except Booking.DoesNotExist:
        return JsonResponse({"error": "Booking not found"}, status=404)



@csrf_exempt
def book_view(request):
    """
    Unified booking view that creates the record and then triggers notifications.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        data = json.loads(request.body)
        service_id = data.get('service_id')
        service = Service.objects.get(id=service_id)
        
        # Create booking in a transaction
        with transaction.atomic():
            booking = Booking.objects.create(
                user=request.user,
                service=service,
                status='WAITING',
                amount=service.price
            )
        
        # --- Notification Logic (Outside Transaction) ---
        customer_name = request.user.full_name or request.user.email
        customer_email = request.user.email
        customer_phone = getattr(request.user, 'phone', 'N/A')
        customer_location = getattr(request.user, 'location', 'N/A')

        agents_notified = 0
        if service.category:
            # Robust filtering for Many-to-Many relationship
            agents = Agent.objects.filter(categories__id=service.category.id, is_available=True).distinct()
            
            for agent in agents:
                accept_link = f"http://localhost:8000/api/booking/{booking.id}/accept/{agent.id}/"
                reject_link = f"http://localhost:8000/api/booking/{booking.id}/reject/{agent.id}/"
                
                subject = f"🚨 New Booking Request: {service.title} | BachMates"
                html_message = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        @media only screen and (max-width: 600px) {{
                            .container {{ width: 100% !important; border-radius: 0 !important; }}
                            .content {{ padding: 20px !important; }}
                            .button-container {{ display: block !important; }}
                            .button {{ width: 100% !important; margin-bottom: 10px !important; display: block !important; text-align: center !important; padding: 16px 0 !important; box-sizing: border-box; }}
                        }}
                    </style>
                </head>
                <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%">
                        <tr>
                            <td style="padding: 20px 0;">
                                <table align="center" border="0" cellpadding="0" cellspacing="0" class="container" style="width: 600px; background-color: #ffffff; border-radius: 24px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">
                                    <tr>
                                        <td style="background: linear-gradient(135deg, #5c62f1, #3b82f6); padding: 40px; text-align: center; color: #ffffff;">
                                            <h1 style="margin: 0; font-size: 28px; font-weight: 900; letter-spacing: -0.02em;">New Job Alert!</h1>
                                            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Expertise Requested: {service.category.name}</p>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td class="content" style="padding: 40px;">
                                            <p style="font-size: 18px; color: #1e293b;">Hello <strong>{agent.name}</strong>,</p>
                                            <p style="color: #64748b; font-size: 16px; line-height: 1.6;">A customer has requested your professional expertise for <strong>{service.title}</strong>.</p>
                                            
                                            <div style="background-color: #f8fafc; border: 1px solid #f1f5f9; border-radius: 20px; padding: 25px; margin: 30px 0;">
                                                <h4 style="margin: 0 0 20px 0; color: #1e293b; font-size: 14px; text-transform: uppercase; letter-spacing: 0.1em;">Customer Details</h4>
                                                <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                                    <tr>
                                                        <td style="padding: 8px 0; color: #94a3b8; font-size: 14px; width: 100px;">Name</td>
                                                        <td style="padding: 8px 0; color: #1e293b; font-weight: 700;">{customer_name}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">Email</td>
                                                        <td style="padding: 8px 0; color: #1e293b; font-weight: 700;">{customer_email}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">Phone</td>
                                                        <td style="padding: 8px 0; color: #1e293b; font-weight: 700;">{customer_phone}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">Location</td>
                                                        <td style="padding: 8px 0; color: #1e293b; font-weight: 700;">{customer_location}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 16px 0 8px 0; color: #94a3b8; font-size: 14px;">Payout</td>
                                                        <td style="padding: 16px 0 8px 0; color: #22c55e; font-weight: 900; font-size: 18px;">₹{service.price}</td>
                                                    </tr>
                                                </table>
                                            </div>
                                            
                                            <div class="button-container" style="margin-top: 40px; text-align: center;">
                                                <a href="{accept_link}" class="button" style="display: inline-block; background-color: #22c55e; color: #ffffff; padding: 16px 35px; border-radius: 14px; font-weight: 800; text-decoration: none; font-size: 16px; box-shadow: 0 10px 20px rgba(34,197,94,0.2);">✅ Accept Job</a>
                                                <span style="display: inline-block; width: 10px;"></span>
                                                <a href="{reject_link}" class="button" style="display: inline-block; background-color: #ef4444; color: #ffffff; padding: 16px 35px; border-radius: 14px; font-weight: 800; text-decoration: none; font-size: 16px;">❌ Decline</a>
                                            </div>
                                            
                                            <p style="margin-top: 40px; color: #94a3b8; font-size: 13px; text-align: center;">
                                                Please respond quickly. This request has been sent to multiple qualified agents in your area.
                                            </p>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #f1f5f9;">
                                            <p style="margin: 0; color: #94a3b8; font-size: 12px; font-weight: 600;">BachMates &mdash; Live Service Platform</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
                """
                
                try:
                    from django.core.mail import EmailMultiAlternatives
                    msg = EmailMultiAlternatives(
                        subject=subject,
                        body=f"New booking for {service.title}. Accept at: {accept_link}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[agent.email]
                    )
                    msg.attach_alternative(html_message, "text/html")
                    msg.send(fail_silently=False) # Changed to False to see errors in console
                    agents_notified += 1
                except Exception as email_err:
                    print(f"[CRITICAL EMAIL ERROR] for {agent.email}: {email_err}")

        return JsonResponse({
            "message": "Searching for professional...",
            "booking_id": booking.id,
            "status": booking.status,
            "service_title": service.title,
            "agents_notified": agents_notified,
            "amount": float(booking.amount)
        })

    except Service.DoesNotExist:
        return JsonResponse({"error": "Service not found"}, status=404)
    except Exception as e:
        print(f"[ERROR] book_view: {e}")
        return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

def bookings_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    
    if request.method == "GET":
        bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
        bookings_data = [{
            "id": b.id,
            "service_title": b.service.title,
            "status": b.status,
            "assigned_agent": b.assigned_agent.name if b.assigned_agent else None,
            "created_at": b.created_at.isoformat()
        } for b in bookings]
        return JsonResponse({"bookings": bookings_data})
    
    return JsonResponse({"error": "Method not allowed"}, status=405)

def get_booking_detail(request, pk):
    try:
        b = Booking.objects.get(pk=pk)
        return JsonResponse({
            "id": b.id,
            "service_title": b.service.title,
            "status": b.status,
            "assigned_agent": b.assigned_agent.name if b.assigned_agent else None,
            "assigned_agent_email": b.assigned_agent.email if b.assigned_agent else None,
            "amount": float(b.amount),
            "rejection_count": b.rejection_count,
            "created_at": b.created_at.isoformat()  # Fix: convert datetime to string
        })
    except Booking.DoesNotExist:
        return JsonResponse({"error": "Booking not found"}, status=404)

@require_http_methods(["GET"])
def agent_accept_booking(request, pk, agent_id):
    # Step 1: Atomically update the booking status
    html_to_return = None
    error_response = None

    try:
        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(pk=pk)

            if booking.status != 'WAITING':
                error_response = 'already_taken'
            else:
                booking.status = 'ACCEPTED'
                if agent_id and agent_id != 0:
                    try:
                        agent_obj = Agent.objects.get(id=agent_id)
                        booking.assigned_agent = agent_obj
                    except Agent.DoesNotExist:
                        pass
                booking.save()

    except Booking.DoesNotExist:
        return HttpResponse("<h2 style='font-family:sans-serif;padding:40px;'>Booking not found.</h2>", status=404)

    # Step 2: Return response OUTSIDE the transaction
    if error_response == 'already_taken':
        return HttpResponse("""
        <!DOCTYPE html><html><head><meta charset="UTF-8">
        <style>*{box-sizing:border-box;margin:0;padding:0;}
        body{font-family:'Segoe UI',sans-serif;display:flex;align-items:center;justify-content:center;
             min-height:100vh;background:linear-gradient(135deg,#0f0c29,#302b63);padding:20px;}
        .card{background:white;border-radius:24px;padding:40px;text-align:center;max-width:400px;
              width:100%;box-shadow:0 30px 60px rgba(0,0,0,0.4);}
        .icon{font-size:52px;margin-bottom:16px;}
        h2{color:#f59e0b;margin-bottom:12px;font-size:22px;font-weight:800;}
        p{color:#64748b;font-size:15px;line-height:1.6;}</style></head>
        <body><div class="card">
          <div class="icon">&#9888;</div>
          <h2>Already Taken</h2>
          <p>This booking has already been accepted by another agent. Thank you for your response!</p>
        </div></body></html>
        """)

    # Reload booking for display (outside transaction)
    try:
        booking = Booking.objects.get(pk=pk)
    except Booking.DoesNotExist:
        return HttpResponse("<h2>Booking not found.</h2>", status=404)

    # Schedule follow-up if agent assigned
    if booking.assigned_agent:
        schedule_followup_email(booking.id, booking.assigned_agent.id, delay_seconds=420)

    customer = booking.user
    customer_name = customer.full_name or customer.email
    customer_email_addr = customer.email
    customer_phone = getattr(customer, 'phone', '') or 'Not provided'
    customer_location = getattr(customer, 'location', '') or 'Not provided'
    service_title = booking.service.title
    amount = float(booking.amount)
    complete_link = f"http://localhost:8000/api/booking/{booking.id}/complete/{agent_id}/"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Booking Accepted — BachMates</title>
      <style>
        *{{box-sizing:border-box;margin:0;padding:0;}}
        body{{font-family:'Segoe UI',Arial,sans-serif;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;}}
        .card{{background:white;border-radius:24px;max-width:480px;width:100%;overflow:hidden;box-shadow:0 30px 60px rgba(0,0,0,0.4);}}
        .header{{background:linear-gradient(135deg,#22c55e,#16a34a);padding:30px 28px;color:white;text-align:center;}}
        .header .icon{{font-size:52px;margin-bottom:12px;}}
        .header h1{{font-size:24px;font-weight:800;margin-bottom:6px;}}
        .header p{{opacity:0.85;font-size:14px;}}
        .body{{padding:28px;}}
        .section-title{{font-size:11px;font-weight:800;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #f1f5f9;}}
        .info-row{{display:flex;align-items:flex-start;gap:12px;margin-bottom:16px;}}
        .info-icon{{font-size:22px;flex-shrink:0;margin-top:2px;}}
        .info-label{{font-size:11px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;}}
        .info-value{{font-size:16px;font-weight:700;color:#1e293b;margin-top:3px;}}
        .amount-box{{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1px solid #bbf7d0;border-radius:14px;padding:16px 20px;margin:20px 0;display:flex;align-items:center;justify-content:space-between;}}
        .amount-label{{font-size:13px;color:#16a34a;font-weight:700;}}
        .amount-value{{font-size:26px;font-weight:900;color:#15803d;}}
        .btn-complete{{display:block;background:linear-gradient(135deg,#5c62f1,#7c3aed);color:white;text-decoration:none;text-align:center;padding:16px;border-radius:14px;font-size:15px;font-weight:800;margin-top:8px;box-shadow:0 8px 20px rgba(92,98,241,0.3);}}
        .footer{{background:#f8faff;padding:16px;text-align:center;font-size:12px;color:#94a3b8;}}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <div class="icon">&#x2705;</div>
          <h1>Booking Accepted!</h1>
          <p>You accepted Booking #{booking.id} &mdash; {service_title}</p>
        </div>
        <div class="body">
          <div class="section-title">&#x1f464; Customer Information</div>

          <div class="info-row">
            <span class="info-icon">&#x1f464;</span>
            <div><div class="info-label">Full Name</div><div class="info-value">{customer_name}</div></div>
          </div>

          <div class="info-row">
            <span class="info-icon">&#x1f4e7;</span>
            <div><div class="info-label">Email</div><div class="info-value">{customer_email_addr}</div></div>
          </div>

          <div class="info-row">
            <span class="info-icon">&#x1f4de;</span>
            <div><div class="info-label">Phone</div><div class="info-value">{customer_phone}</div></div>
          </div>

          <div class="info-row">
            <span class="info-icon">&#x1f4cd;</span>
            <div><div class="info-label">Location</div><div class="info-value">{customer_location}</div></div>
          </div>

          <div class="info-row">
            <span class="info-icon">&#x1f6e0;&#xfe0f;</span>
            <div><div class="info-label">Service</div><div class="info-value">{service_title}</div></div>
          </div>

          <div class="amount-box">
            <span class="amount-label">Service Amount</span>
            <span class="amount-value">&#x20b9;{amount:.2f}</span>
          </div>

          <a href="{complete_link}" class="btn-complete">&#x1f3c1; Mark Job as Completed</a>
        </div>
        <div class="footer">BachMates &mdash; Live Service Booking Platform</div>
      </div>
    </body>
    </html>
    """
    return HttpResponse(html)

@require_http_methods(["GET"])
def agent_reject_booking(request, pk, agent_id):
    try:
        booking = Booking.objects.get(pk=pk)
        booking.rejection_count += 1
        booking.save()
    except Booking.DoesNotExist:
        pass

    return HttpResponse("""
    <!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>*{box-sizing:border-box;margin:0;padding:0;}
    body{font-family:'Segoe UI',sans-serif;display:flex;align-items:center;justify-content:center;
         min-height:100vh;background:linear-gradient(135deg,#0f0c29,#302b63);padding:20px;}
    .card{background:white;border-radius:24px;padding:40px;text-align:center;max-width:400px;
          width:100%;box-shadow:0 30px 60px rgba(0,0,0,0.4);}
    .icon{font-size:52px;margin-bottom:16px;}
    h2{color:#64748b;margin-bottom:12px;font-size:22px;font-weight:800;}
    p{color:#94a3b8;font-size:15px;line-height:1.6;}
    .footer{margin-top:24px;font-size:12px;color:#cbd5e1;}</style></head>
    <body><div class="card">
      <div class="icon">&#x274c;</div>
      <h2>Booking Rejected</h2>
      <p>You have passed on this booking. Another agent may still accept it.</p>
      <div class="footer">BachMates &mdash; Live Service Booking Platform</div>
    </div></body></html>
    """)

@require_http_methods(["GET"])
def agent_complete_booking(request, pk, agent_id):
    try:
        booking = Booking.objects.get(pk=pk)
        # Check if already completed
        if booking.status == 'COMPLETED':
            pass
        elif booking.assigned_agent and booking.assigned_agent.id == agent_id:
            booking.status = 'COMPLETED'
            booking.save()
        else:
            return HttpResponse("<h2>Unauthorized or invalid agent.</h2>", status=403)
            
        return HttpResponse("""
        <!DOCTYPE html><html><head><meta charset="UTF-8">
        <style>*{box-sizing:border-box;margin:0;padding:0;}
        body{font-family:'Segoe UI',sans-serif;display:flex;align-items:center;justify-content:center;
             min-height:100vh;background:linear-gradient(135deg,#00b09b,#96c93d);padding:20px;}
        .card{background:white;border-radius:24px;padding:40px;text-align:center;max-width:400px;
              width:100%;box-shadow:0 30px 60px rgba(0,0,0,0.2);}
        .icon{font-size:60px;margin-bottom:20px;}
        h2{color:#2d3436;margin-bottom:12px;font-size:24px;font-weight:900;}
        p{color:#636e72;font-size:16px;line-height:1.6;margin-bottom:20px;}
        .badge{display:inline-block;padding:8px 20px;background:#e1f7ef;color:#00b09b;border-radius:50px;font-weight:800;font-size:14px;}</style></head>
        <body><div class="card">
          <div class="icon">🏆</div>
          <h2>Great Job!</h2>
          <p>The work has been marked as completed. The customer has been notified to proceed with payment.</p>
          <div class="badge">Job Completed</div>
        </div></body></html>
        """)
    except Booking.DoesNotExist:
        return HttpResponse("<h2>Booking not found.</h2>", status=404)

@csrf_exempt
def admin_agents_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "Admin only"}, status=403)
    
    if request.method == "GET":
        agents = Agent.objects.all()
        data = []
        for a in agents:
            data.append({
                "id": a.id,
                "name": a.name,
                "email": a.email,
                "phone": a.phone,
                "categories": [c.name for c in a.categories.all()],
                "category_ids": [c.id for c in a.categories.all()],
                "is_available": a.is_available
            })
        return JsonResponse({"agents": data})
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            agent = Agent.objects.create(
                name=data.get('name'),
                email=data.get('email'),
                phone=data.get('phone', ''),
                is_available=True
            )
            cat_ids = data.get('category_ids', [])
            if cat_ids:
                agent.categories.set(Category.objects.filter(id__in=cat_ids))
            
            return JsonResponse({"message": "Agent added successfully", "id": agent.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def admin_agent_delete_view(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "Admin only"}, status=403)
    
    if request.method == "DELETE":
        try:
            Agent.objects.get(pk=pk).delete()
            return JsonResponse({"message": "Agent deleted"})
        except Agent.DoesNotExist:
            return JsonResponse({"error": "Agent not found"}, status=404)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def update_profile_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    import json
    try:
        data = json.loads(request.body)
        user = request.user
        
        user.full_name = data.get("full_name", user.full_name)
        user.email = data.get("email", user.email)
        user.phone = data.get("phone", user.phone)
        user.location = data.get("location", user.location)
        
        user.save()
        
        return JsonResponse({
            "message": "Profile updated successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "location": user.location,
                "isAdmin": user.is_staff or user.is_superuser
            }
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def cancel_booking_view(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        booking = Booking.objects.get(pk=pk)
        
        # If the booking was already accepted, notify the agent
        if booking.status == 'ACCEPTED' and booking.assigned_agent:
            try:
                agent_email = booking.assigned_agent.email
                service_name = booking.service.title
                
                subject = f'Service Cancelled: {service_name}'
                message = f'Hello {booking.assigned_agent.name},\n\nYour service for {service_name} will be cancelled. Please don\'t go to the location. \n\nWait for another service request in the meantime.\n\nThank you,\nBachMates Team'
                
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [agent_email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending cancellation email to agent: {e}")

        if booking.status in ['WAITING', 'ACCEPTED']:
            booking.delete()
            return JsonResponse({"message": "Booking cancelled successfully"})
        else:
            return JsonResponse({"error": f"Cannot cancel booking in '{booking.status}' status"}, status=400)
            
    except Booking.DoesNotExist:
        return JsonResponse({"error": "Booking not found"}, status=404)


