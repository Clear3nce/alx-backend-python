from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, logout
from .models import Message
from .utils import get_thread

from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from django.db.models import Prefetch, Q, Count
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.core.cache import cache


User = get_user_model()

def message_history(request, message_id):
    message = get_object_or_404(Message, pk=message_id)
    history = message.history.all().order_by('-edited_at')
    return render(request, 'message_history.html', {'message': message, 'history': history})


@login_required
def edit_message(request, message_id):
    message = get_object_or_404(Message, pk=message_id, sender=request.user)

    if request.method == "POST":
        new_content = request.POST['content']
        message.content = new_content
        message.edited_by = request.user
        message.save()
        return redirect('inbox')  # or wherever

    return render(request, 'edit_message.html', {'message': message})



@login_required
def delete_user(request):
    if request.method == "POST":
        user = request.user
        logout(request)         # End the session first
        user.delete()           # Delete the user from DB
        return redirect('account_deleted')  # Redirect to confirmation page
    return render(request, 'delete_user.html')  # Show a confirmation form




@login_required
def reply_message(request, parent_id):
    parent = get_object_or_404(Message, pk=parent_id)
    if request.method == "POST":
        Message.objects.create(
            sender=request.user,
            receiver=parent.receiver,
            content=request.POST['content'],
            parent_message=parent
        )
        return redirect('message_detail', message_id=parent_id)
    



@login_required
def unread_inbox(request):
    unread_messages = Message.unread.unread_for_user(request.user).only('id', 'sender', 'content', 'timestamp')
    return render(request, 'unread_inbox.html', {
        'messages': unread_messages
    })



def get_message_thread(message):
    """
    Recursively collects all replies to a message in a threaded format.
    Returns a list of (message, depth) tuples.
    """
    thread = []

    def recurse(msg, depth=0):
        thread.append((msg, depth))
        replies = msg.replies.select_related('sender').all().order_by('timestamp')
        for reply in replies:
            recurse(reply, depth + 1)

    recurse(message)
    return thread

@login_required
def message_detail(request, message_id):
    root = get_object_or_404(
        Message.objects.select_related('sender', 'receiver'),
        pk=message_id
    )

    thread = get_threaded_replies(root)

    return render(request, 'message_detail.html', {
        'root': root,
        'thread': thread
    })


def get_threaded_replies(root_message):
    """
    Recursively fetch all replies using Message.objects.filter
    and optimize with select_related for sender.
    Returns a list of (message, depth) tuples.
    """
    thread = []

    def recurse(message, depth):
        thread.append((message, depth))

        # ✅ Explicit use of Message.objects.filter
        replies = Message.objects.filter(parent_message=message).select_related('sender').order_by('timestamp')

        for reply in replies:
            recurse(reply, depth + 1)

    recurse(root_message, 0)
    return thread


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OptimizedPagination

    def get_queryset(self):
        """
        Optimized conversation query with caching
        """
        cache_key = f"user_{self.request.user.id}_conversations"
        cached_conversations = cache.get(cache_key)
        
        if cached_conversations is not None:
            return cached_conversations
            
        conversations = Conversation.objects.filter(
            participants=self.request.user
        ).select_related('created_by').prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.unread.for_user(self.request.user),
                to_attr='unread_messages'
            ),
            'participants'
        ).only(
            'id', 'title', 'updated_at', 'created_by__username'
        ).order_by('-updated_at')
        
        cache.set(cache_key, conversations, 60)  # Cache for 60 seconds
        return conversations

    @method_decorator(cache_page(60))
    @action(detail=True, methods=['get'])
    def unread_messages(self, request, pk=None):
        """
        Cached endpoint for unread messages in conversation
        """
        conversation = self.get_object()
        unread_messages = conversation.get_unread_messages(request.user)
        page = self.paginate_queryset(unread_messages)
        serializer = MessageSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @method_decorator(cache_page(60))
    @action(detail=False, methods=['get'])
    def unread_counts(self, request):
        """
        Cached endpoint for unread message counts
        """
        cache_key = f"user_{request.user.id}_unread_counts"
        cached_counts = cache.get(cache_key)
        
        if cached_counts is not None:
            return Response(cached_counts)
            
        conversations = Conversation.objects.filter(
            participants=request.user
        ).annotate(
            unread_count=Count(
                'messages',
                filter=Q(messages__receiver=request.user) & 
                      Q(messages__is_read=False)
            )
        ).only('id', 'title')
        
        data = {
            str(conv.id): conv.unread_count
            for conv in conversations
        }
        
        cache.set(cache_key, data, 60)  # Cache for 60 seconds
        return Response(data)

    @action(detail=True, methods=['post'])
    def mark_all_as_read(self, request, pk=None):
        """
        Mark all messages in conversation as read and clear cache
        """
        conversation = self.get_object()
        unread_messages = conversation.messages.filter(
            receiver=request.user,
            is_read=False
        )
        
        unread_messages.update(is_read=True)
        
        # Clear relevant cache
        cache.delete(f"user_{request.user.id}_unread_messages")
        cache.delete(f"user_{request.user.id}_unread_counts")
        cache.delete(f"user_{request.user.id}_conversations")
        
        return Response(
            {'status': f'{unread_messages.count()} messages marked as read'}
        )

