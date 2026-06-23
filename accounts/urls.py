from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_user, name='logout'),
     path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("reset-password/", views.reset_password_view, name="reset_password"),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    # core/urls.py or accounts/urls.py
    path('dashboard/', views.dashboard, name='dashboard'), # Ensure name='dashboard' is here

    path('services/', views.services, name='services'), # The main list
    path('services/instagram/', views.instagramfollowers, name='instagram_followers'),
    path('services/tiktok/', views.tiktokfollowers, name='tiktok_followers'),
    path('services/twitter/', views.twitterfollowers, name='twitter_followers'),
    path('services/how-to-use/', views.howtouse, name='how_to_use'),
    path('services/blog/', views.blog, name='blog'),
    path('services/refund-policy/', views.refundpolicy, name='refund_policy'),
    path('services/contact-us/', views.contactus, name='contact_us'),
    path('services/terms/', views.terms, name='terms'),
    path('services/privacy-policy/', views.privacypolicy, name='privacy_policy'),
    


]