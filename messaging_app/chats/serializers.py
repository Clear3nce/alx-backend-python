from rest_framework import serializers
from .models import User, Conversation, Message
from rest_framework.exceptions import ValidationError

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'username', 'email', 'first_name', 'last_name']
        extra_kwargs = {'password': {'write_only': True}}

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['message_id', 'conversation', 'sender', 'message_body', 'sent_at', 'read']
        read_only_fields = ['sent_at']

    def validate_message_body(self, value):
        if not value.strip():
            raise ValidationError("Message body cannot be empty")
        return value

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'participants', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class ConversationCreateSerializer(serializers.ModelSerializer):
    participants = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=True
    )

    class Meta:
        model = Conversation
        fields = ['participants']

    def validate_participants(self, value):
        if len(value) < 1:
            raise ValidationError("At least one participant is required")
        return value

class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['conversation', 'message_body']

    def validate(self, data):
        if not data.get('message_body', '').strip():
            raise ValidationError("Message body cannot be empty")
        return data
