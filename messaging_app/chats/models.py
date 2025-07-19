# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Add additional fields here that aren't included in the default User model.
    """
    phone_number = models.CharField(
        _('phone number'),
        max_length=20,
        blank=True,
        null=True,
        unique=True
    )
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to='profile_pics/',
        blank=True,
        null=True
    )
    status = models.CharField(
        _('status'),
        max_length=255,
        blank=True,
        null=True
    )
    last_seen = models.DateTimeField(
        _('last seen'),
        auto_now=True
    )

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')


class Conversation(models.Model):
    """
    Model representing a conversation between users.
    """
    participants = models.ManyToManyField(
        User,
        related_name='conversations',
        verbose_name=_('participants')
    )
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True
    )

    def __str__(self):
        return f"Conversation {self.id}"

    class Meta:
        verbose_name = _('conversation')
        verbose_name_plural = _('conversations')
        ordering = ['-updated_at']


class Message(models.Model):
    """
    Model representing a message in a conversation.
    """
    conversation = models.ForeignKey(
        Conversation,
        related_name='messages',
        on_delete=models.CASCADE,
        verbose_name=_('conversation')
    )
    sender = models.ForeignKey(
        User,
        related_name='sent_messages',
        on_delete=models.CASCADE,
        verbose_name=_('sender')
    )
    content = models.TextField(
        _('content')
    )
    timestamp = models.DateTimeField(
        _('timestamp'),
        auto_now_add=True
    )
    read = models.BooleanField(
        _('read'),
        default=False
    )

    def __str__(self):
        return f"Message from {self.sender} in {self.conversation}"

    class Meta:
        verbose_name = _('message')
        verbose_name_plural = _('messages')
        ordering = ['timestamp']
