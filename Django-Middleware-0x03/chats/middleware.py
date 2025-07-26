"""
Django Middleware for Chat Application
Contains all required middleware classes in one file
"""

import logging
from datetime import datetime
import os
from django.conf import settings
from django.http import HttpResponseForbidden
from collections import defaultdict

# 1. Request Logging Middleware
class RequestLoggingMiddleware:
    """Logs all requests with timestamp, user, and path"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('request_logger')
        
        # Configure logging
        logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        if not self.logger.handlers:
            file_handler = logging.FileHandler(os.path.join(logs_dir, 'requests.log'))
            file_handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)
    
    def __call__(self, request):
        user = request.user.username if request.user.is_authenticated else 'Anonymous'
        self.logger.info(f"{datetime.now()} - User: {user} - Path: {request.path}")
        return self.get_response(request)

# 2. Time Restriction Middleware
class RestrictAccessByTimeMiddleware:
    """Blocks access between 6 PM and 9 PM"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        current_hour = datetime.now().hour
        if 18 <= current_hour < 21:  # 6 PM to 9 PM
            return HttpResponseForbidden(
                "Access to messaging is restricted between 6 PM and 9 PM. "
                "Please try again later."
            )
        return self.get_response(request)

# 3. Rate Limiting Middleware
class OffensiveLanguageMiddleware:
    """Limits users to 5 messages per minute"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = defaultdict(list)
        self.limit = 5  # 5 messages
        self.window = 60  # 1 minute in seconds
    
    def __call__(self, request):
        if request.method == 'POST':
            ip = request.META.get('REMOTE_ADDR')
            now = datetime.now().timestamp()
            
            # Remove old timestamps
            self.request_counts[ip] = [t for t in self.request_counts[ip] if now - t < self.window]
            
            # Check limit
            if len(self.request_counts[ip]) >= self.limit:
                return HttpResponseForbidden(
                    "Message limit exceeded (5 per minute). Please wait."
                )
            
            self.request_counts[ip].append(now)
        
        return self.get_response(request)

# 4. Role Permission Middleware
class RolepermissionMiddleware:
    """Restricts routes to admin/moderator users"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.protected_paths = [
            '/admin/',
            '/moderate/',
            '/api/chat/delete/'
        ]
    
    def __call__(self, request):
        if any(request.path.startswith(path) for path in self.protected_paths):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Authentication required")
            
            if not hasattr(request.user, 'role'):
                return HttpResponseForbidden("User role not defined")
            
            if request.user.role not in ['admin', 'moderator']:
                return HttpResponseForbidden("Admin or moderator privileges required")
        
        return self.get_response(request)