from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('이메일은 필수입니다.')
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Provider(models.TextChoices):
        LOCAL = 'local', '이메일'
        KAKAO = 'kakao', '카카오'

    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=30)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    provider = models.CharField(max_length=10, choices=Provider.choices, default=Provider.LOCAL)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nickname']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
