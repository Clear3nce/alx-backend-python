from rest_framework import serializers
from .models import User, Conversation, Message
from rest_framework.exceptions import ValidationError

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    status = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = [
            'user_id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone_number',
            'profile_picture',
            'status',
            'last_seen'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'last_seen': {'read_only': True}
        }

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    message_body = serializers.CharField(required=True)
    is_own_message = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'message_id',
            'conversation',
            'sender',
            'message_body',
            'sent_at',
            'read',
            'is_own_message'
        ]
        read_only_fields = ['sent_at', 'sender']

    def get_is_own_message(self, obj):
        request = self.context.get('request')
        return request and request.user == obj.sender

    def validate_message_body(self, value):
        if not value.strip():
            raise ValidationError("Message body cannot be empty")
        return value

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'conversation_id',
            'participants',
            'title',
            'created_at',
            'updated_at',
            'messages',
            'last_message'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_messages(self, obj):
        messages = obj.messages.all().order_by('-sent_at')[:50]
        return MessageSerializer(messages, many=True, context=self.context).data

    def get_title(self, obj):
        request = self.context.get('request')
        if request and request.user:
            participants = obj.participants.exclude(pk=request.user.pk)
            return ", ".join([p.username for p in participants])
        return "Group Conversation"

    def get_last_message(self, obj):
        last_message = obj.messages.order_by('-sent_at').first()
        if last_message:
            return MessageSerializer(last_message, context=self.context).data
        return None

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
    message_body = serializers.CharField(required=True)

    class Meta:
        model = Message
        fields = ['conversation', 'message_body']
        extra_kwargs = {
            'conversation': {'required': True},
            'message_body': {'required': True}
        }

    def validate(self, data):
        if not data.get('conversation') or not data.get('message_body'):
            raise ValidationError("Both conversation and message body are required")
        return data
