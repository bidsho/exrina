from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings

from .models import User, PasswordResetCode
from .password_forms import ForgotPasswordForm, ResetPasswordForm
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from wallets.models import Wallet
from orders.models import Order
from django.contrib import messages

from django.contrib.auth import logout




def index(request):
    return render(request, "pages/index.html")

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        
        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')   
        else:
            messages.error(request, "Invalid username or password.")
            
    return render(request, 'accounts/login.html')
def signup_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        e = request.POST.get('email')
        p = request.POST.get('password')
        
        if User.objects.filter(username=u).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'accounts/signup.html')
        
        if User.objects.filter(email=e).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'accounts/signup.html')
        
        user = User.objects.create_user(username=u, email=e, password=p)
        login(request, user)
        messages.success(request, f"Account created for {user.username}!")
        return redirect('dashboard')
    
    return render(request, 'accounts/signup.html')



def logout_user(request):
    logout(request)
    messages.info(request, "You have been logged out. See you soon!")
    return redirect('index') # Redirect to your new landing page

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

@login_required
def student_dashboard(request):
    if not request.user.is_student:
        return HttpResponseForbidden("You must be a student to access this page.")
    return render(request, "dashboard/student.html")




@login_required
def dashboard(request):
    # 1. Get the wallet
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # 2. Get the user's latest 5 orders for the dashboard table
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # 3. Pass BOTH wallet and recent_orders to the template
    return render(request, "dashboard/dashboard.html", {
        'wallet': wallet,
        'recent_orders': recent_orders
    })

@login_required
def teacher_dashboard(request):
    if not request.user.is_teacher:
        return HttpResponseForbidden("You must be a teacher to access this page.")
    return render(request, "dashboard/teacher.html")


# ✅ Step 1: user enters email -> send 6-digit code (HTML email)
def forgot_password_view(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "No account found with that email.")
                return render(request, "accounts/forgot_password.html", {"form": form})

            # Create new code
            code = PasswordResetCode.generate_code()
            PasswordResetCode.objects.create(user=user, code=code)

            expiry_minutes = 10

            # Plain text fallback
            text_message = (
                f"Your password reset code is: {code}\n"
                f"This code expires in {expiry_minutes} minutes."
            )

            # HTML email
            html_message = render_to_string("emails/password_reset_code.html", {
                "name": user.first_name or user.username,
                "code": code,
                "minutes": expiry_minutes,
                "year": timezone.now().year,
                "reset_url": None,  # you can add a link later if you want
            })

            msg = EmailMultiAlternatives(
                subject="Password Reset Code",
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send()

            messages.success(request, "We sent a reset code to your email.")
            return redirect("reset_password")

    else:
        form = ForgotPasswordForm()

    return render(request, "accounts/forgot_password.html", {"form": form})


# ✅ Step 2: user enters email + code + new password
def reset_password_view(request):
    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            code = form.cleaned_data["code"].strip()
            new_password = form.cleaned_data["new_password1"]

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "Invalid email or code.")
                return render(request, "accounts/reset_password.html", {"form": form})

            reset_obj = PasswordResetCode.objects.filter(
                user=user, code=code, is_used=False
            ).order_by("-created_at").first()

            if not reset_obj:
                messages.error(request, "Invalid code.")
                return render(request, "accounts/reset_password.html", {"form": form})

            if reset_obj.is_expired():
                messages.error(request, "Code expired. Please request a new one.")
                return redirect("forgot_password")

            # Set password securely
            user.set_password(new_password)
            user.save()

            # Mark code used
            reset_obj.is_used = True
            reset_obj.save()

            messages.success(request, "Password updated successfully. Please login.")
            return redirect("login")

    else:
        form = ResetPasswordForm()

    return render(request, "accounts/reset_password.html", {"form": form})

def instagramfollowers(request):
    return render(request, "services/instagram_followers.html")

def tiktokfollowers(request):
    return render(request, "services/tiktok_followers.html")

def twitterfollowers(request):
    return render(request, "services/twitter_followers.html")

def services(request):
    return render(request, "services/services.html")

def howtouse(request):
    return render(request, "services/how_to_use.html")

def blog(request):
    return render(request, "services/blog.html")
def refundpolicy(request):
    return render(request, "services/refund_policy.html")
def contactus(request):
    return render(request, "services/contact_us.html")
def terms(request):
    return render(request, "services/terms.html")
def privacypolicy(request):
    return render(request, "services/privacy_policy.html")