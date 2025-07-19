import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    """
    user_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    email = models.EmailField(
        _('email address'),
        unique=True
    )
    password = models.CharField(
        _('password'),
        max_length=128
    )
    first_name = models.CharField(
        _('first name'),
        max_length=150,
        blank=True
    )
    last_name = models.CharField(
        _('last name'),
        max_length=150,
        blank=True
    )
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
    conversation_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
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
        return f"Conversation {self.conversation_id}"

    class Meta:
        verbose_name = _('conversation')
        verbose_name_plural = _('conversations')
        ordering = ['-updated_at']


class Message(models.Model):
    """
    Model representing a message in a conversation.
    """
    message_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
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
    message_body = models.TextField(
        _('message body')
    )
    sent_at = models.DateTimeField(
        _('sent at'),
        auto_now_add=True
    )
    read = models.BooleanField(
        _('read'),
        default=False
    )

    def __str__(self):
        return f"Message {self.message_id} from {self.sender}"

    class Meta:
        verbose_name = _('message')
        verbose_name_plural = _('messages')
        ordering = ['sent_at']