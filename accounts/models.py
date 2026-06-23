from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
import random

class User(AbstractUser):
    # Use UUIDs for the primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, blank=True)
    
    
    # Profile Picture
   
    profile_pic = models.ImageField(
        upload_to='profile_pics/',   # stored inside MEDIA/profile_pics/
        null=True,
        blank=True
    )

    def __str__(self):
        return self.username


class PasswordResetCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        # Expires after 10 minutes
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)

    @staticmethod
    def generate_code():
        return f"{random.randint(100000, 999999)}"  