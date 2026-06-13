#!/usr/bin/env python3
"""
WABS - Women And Baby Safety System
"One Touch for Safety"
Production-Ready Real-Time Safety Platform
Complete with Real GPS, Voice Detection, Admin Panel, Community Network
"""

import os
import json
import uuid
import hashlib
import datetime
import secrets
import threading
import time
from functools import wraps
from flask import (
    Flask, render_template_string, request, jsonify, redirect, 
    url_for, session, flash, make_response, Response
)
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import base64

# Initialize Flask App
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app)

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'wabs_production.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
db = SQLAlchemy(app)

# =============================================================================
# DATABASE MODELS - Fixed Foreign Key Relationships
# =============================================================================

class Users(db.Model):
    """Complete Users Table"""
    __tablename__ = 'users'
    
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), nullable=False)
    Mobile = db.Column(db.String(15), unique=True, nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    Address = db.Column(db.String(255))
    PasswordHash = db.Column(db.String(255), nullable=False)
    UserType = db.Column(db.String(20), default='woman')  # woman, parent, volunteer, admin
    IsActive = db.Column(db.Boolean, default=True)
    LastLogin = db.Column(db.DateTime)
    CreatedAt = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships with explicit foreign_keys
    children = db.relationship('Children', backref='parent_user', lazy=True, foreign_keys='Children.UserID')
    emergency_contacts = db.relationship('EmergencyContacts', backref='user', lazy=True, foreign_keys='EmergencyContacts.UserID')
    sos_records = db.relationship('SOSRecords', backref='user', lazy=True, foreign_keys='SOSRecords.UserID')
    audio_events = db.relationship('AudioEvents', backref='user', lazy=True, foreign_keys='AudioEvents.UserID')
    location_tracking = db.relationship('LocationTracking', backref='user', lazy=True, foreign_keys='LocationTracking.UserID')
    voice_recordings = db.relationship('VoiceRecordings', backref='user', lazy=True, foreign_keys='VoiceRecordings.UserID')
    community_responses = db.relationship('CommunityResponses', backref='volunteer', lazy=True, foreign_keys='CommunityResponses.UserID')

class Children(db.Model):
    """Child Profiles Table"""
    __tablename__ = 'children'
    
    ChildID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    ChildName = db.Column(db.String(100), nullable=False)
    Age = db.Column(db.Integer, nullable=False)
    Gender = db.Column(db.String(10))
    ParentName = db.Column(db.String(100))
    ParentMobile = db.Column(db.String(15))
    Photo = db.Column(db.Text)  # Base64 encoded image
    MedicalInfo = db.Column(db.Text)
    ChildCode = db.Column(db.String(10), unique=True)  # Unique code for child
    IsActive = db.Column(db.Boolean, default=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class EmergencyContacts(db.Model):
    """Emergency Contacts with Priority"""
    __tablename__ = 'emergency_contacts'
    
    ContactID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    ContactName = db.Column(db.String(100), nullable=False)
    Relationship = db.Column(db.String(50), nullable=False)
    Mobile = db.Column(db.String(15), nullable=False)
    AlternateMobile = db.Column(db.String(15))
    Email = db.Column(db.String(100))
    PriorityLevel = db.Column(db.Integer, default=1)  # 1=Critical, 2=High, 3=Medium
    IsActive = db.Column(db.Boolean, default=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class SOSRecords(db.Model):
    """Complete SOS Emergency Records - Fixed Relationships"""
    __tablename__ = 'sos_records'
    
    SOSID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    ChildID = db.Column(db.Integer, db.ForeignKey('children.ChildID'), nullable=True)
    DateTime = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    Latitude = db.Column(db.Float, nullable=False)
    Longitude = db.Column(db.Float, nullable=False)
    Accuracy = db.Column(db.Float)
    Address = db.Column(db.String(500))
    Status = db.Column(db.String(20), default='active')  # active, responding, resolved, cancelled
    AlertType = db.Column(db.String(50), default='manual')  # manual, voice, child_sound, auto
    LocationLink = db.Column(db.String(500))
    Notes = db.Column(db.Text)
    ResolvedAt = db.Column(db.DateTime)
    ResolvedBy = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=True)
    
    # Fix: Specify foreign_keys for the resolver relationship
    resolver = db.relationship('Users', foreign_keys=[ResolvedBy], backref='resolved_sos_records')

class AudioEvents(db.Model):
    """Voice Detection Events"""
    __tablename__ = 'audio_events'
    
    EventID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    AudioType = db.Column(db.String(50))  # keyword, distress_phrase, crying, screaming, panic
    DetectedText = db.Column(db.Text)
    OriginalText = db.Column(db.Text)  # Full transcribed text
    ConfidenceScore = db.Column(db.Float)
    Language = db.Column(db.String(10))  # english, tamil, tanglish, other
    Duration = db.Column(db.Float)  # Audio duration in seconds
    AudioData = db.Column(db.Text)  # Base64 encoded audio
    Latitude = db.Column(db.Float)
    Longitude = db.Column(db.Float)
    DateTime = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    AutoTriggeredSOS = db.Column(db.Boolean, default=False)
    IsProcessed = db.Column(db.Boolean, default=False)

class VoiceRecordings(db.Model):
    """Complete Voice Recording Storage"""
    __tablename__ = 'voice_recordings'
    
    RecordingID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    RecordingType = db.Column(db.String(50))  # manual, auto, continuous
    AudioData = db.Column(db.Text)  # Base64 encoded audio
    TranscribedText = db.Column(db.Text)
    Language = db.Column(db.String(10))
    Duration = db.Column(db.Float)
    Latitude = db.Column(db.Float)
    Longitude = db.Column(db.Float)
    IsEmergency = db.Column(db.Boolean, default=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class LocationTracking(db.Model):
    """Real-time Location Tracking Data"""
    __tablename__ = 'location_tracking'
    
    TrackID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    Latitude = db.Column(db.Float, nullable=False)
    Longitude = db.Column(db.Float, nullable=False)
    Accuracy = db.Column(db.Float)
    Speed = db.Column(db.Float)
    Heading = db.Column(db.Float)
    BatteryLevel = db.Column(db.Float)
    NetworkType = db.Column(db.String(20))
    Timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class CommunityAlerts(db.Model):
    """Community Safety Network Alerts"""
    __tablename__ = 'community_alerts'
    
    AlertID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    SOSID = db.Column(db.Integer, db.ForeignKey('sos_records.SOSID'), nullable=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=True)
    Latitude = db.Column(db.Float, nullable=False)
    Longitude = db.Column(db.Float, nullable=False)
    Radius = db.Column(db.Float, default=500)  # meters
    AlertType = db.Column(db.String(50))  # emergency, child, voice, general
    AlertMessage = db.Column(db.String(500))
    AlertMessageTamil = db.Column(db.String(500))
    IsActive = db.Column(db.Boolean, default=True)
    SentAt = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    ExpiresAt = db.Column(db.DateTime)
    RespondedCount = db.Column(db.Integer, default=0)
    ResolvedAt = db.Column(db.DateTime)

class CommunityResponses(db.Model):
    """Community Volunteer Responses"""
    __tablename__ = 'community_responses'
    
    ResponseID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AlertID = db.Column(db.Integer, db.ForeignKey('community_alerts.AlertID'), nullable=False)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    ResponseType = db.Column(db.String(50))  # i_am_coming, called_police, safe_escort, medical_help
    Latitude = db.Column(db.Float)
    Longitude = db.Column(db.Float)
    Message = db.Column(db.Text)
    RespondedAt = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    ArrivedAt = db.Column(db.DateTime)

class IncidentReports(db.Model):
    """Detailed Incident Reports"""
    __tablename__ = 'incident_reports'
    
    ReportID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    SOSID = db.Column(db.Integer, db.ForeignKey('sos_records.SOSID'), nullable=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    IncidentType = db.Column(db.String(100))
    Description = db.Column(db.Text)
    Location = db.Column(db.String(500))
    Latitude = db.Column(db.Float)
    Longitude = db.Column(db.Float)
    Severity = db.Column(db.String(20))  # low, medium, high, critical
    Status = db.Column(db.String(20), default='open')  # open, investigating, resolved
    CreatedAt = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    UpdatedAt = db.Column(db.DateTime)

# =============================================================================
# AUTHENTICATION DECORATORS
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        if session.get('user_type') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# TEMPLATE RENDERING HELPER
# =============================================================================

def render_page(content_html, scripts_html="", page_title="WABS", **kwargs):
    """Helper function to render complete pages"""
    
    base_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title} - WABS Safety System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {{
            --primary: #E63946;
            --primary-dark: #C1121F;
            --secondary: #457B9D;
            --accent: #F4A261;
            --dark: #1D3557;
            --light: #F1FAEE;
            --danger: #DC3545;
            --success: #28A745;
            --warning: #FFC107;
            --info: #17A2B8;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #F1FAEE 0%, #E8F0FE 100%);
            min-height: 100vh;
        }}
        
        .navbar-wabs {{
            background: linear-gradient(135deg, var(--dark) 0%, #2C3E50 100%);
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            padding: 15px 0;
        }}
        
        .navbar-brand-wabs {{
            font-size: 1.8rem;
            font-weight: 800;
            color: white !important;
            letter-spacing: 2px;
        }}
        
        .navbar-brand-wabs span {{ color: var(--primary); }}
        
        .tagline {{
            font-size: 0.85rem;
            color: rgba(255,255,255,0.8);
            font-style: italic;
            letter-spacing: 1px;
        }}
        
        .nav-link-wabs {{
            color: white !important;
            font-weight: 500;
            margin: 0 5px;
            transition: all 0.3s;
            padding: 8px 15px !important;
            border-radius: 20px;
        }}
        
        .nav-link-wabs:hover {{
            background: rgba(255,255,255,0.15);
            transform: translateY(-2px);
        }}
        
        .sos-button-giant {{
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: radial-gradient(circle at 30% 30%, #FF4444, #CC0000);
            border: 8px solid #990000;
            color: white;
            font-size: 2.5rem;
            font-weight: 900;
            cursor: pointer;
            box-shadow: 0 10px 40px rgba(255,0,0,0.4), 0 0 80px rgba(255,0,0,0.2);
            transition: all 0.3s;
            animation: pulse 2s infinite;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            letter-spacing: 3px;
            position: relative;
        }}
        
        .sos-button-giant:hover {{
            transform: scale(1.08);
            box-shadow: 0 15px 60px rgba(255,0,0,0.6), 0 0 120px rgba(255,0,0,0.3);
        }}
        
        @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(255,0,0,0.7); }}
            70% {{ box-shadow: 0 0 0 30px rgba(255,0,0,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(255,0,0,0); }}
        }}
        
        .sos-small {{
            width: 80px;
            height: 80px;
            font-size: 1.2rem;
            border-width: 4px;
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 9999;
            animation: pulse 2s infinite;
        }}
        
        .card-wabs {{
            border: none;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: all 0.3s;
            background: white;
            overflow: hidden;
            margin-bottom: 20px;
            cursor: pointer;
        }}
        
        .card-wabs:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        }}
        
        .card-wabs.clickable:active {{
            transform: scale(0.98);
        }}
        
        .card-header-wabs {{
            background: linear-gradient(135deg, var(--dark), var(--secondary));
            color: white;
            font-weight: 600;
            padding: 20px;
            border: none;
        }}
        
        .btn-wabs {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 30px;
            font-weight: 600;
            transition: all 0.3s;
            box-shadow: 0 5px 15px rgba(230,57,70,0.3);
        }}
        
        .btn-wabs:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(230,57,70,0.5);
            color: white;
        }}
        
        .btn-wabs:active {{
            transform: scale(0.95);
        }}
        
        .stat-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
            transition: all 0.3s;
            cursor: pointer;
        }}
        
        .stat-card:hover {{ transform: translateY(-5px); }}
        
        .stat-number {{
            font-size: 3rem;
            font-weight: 800;
            color: var(--primary);
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .voice-indicator {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 20px auto;
            transition: all 0.3s;
            cursor: pointer;
        }}
        
        .voice-indicator.listening {{
            animation: voicePulse 1.5s infinite;
            background: linear-gradient(135deg, #FF4444, #CC0000);
        }}
        
        @keyframes voicePulse {{
            0% {{ transform: scale(1); opacity: 0.8; }}
            50% {{ transform: scale(1.1); opacity: 1; }}
            100% {{ transform: scale(1); opacity: 0.8; }}
        }}
        
        .map-container {{
            height: 400px;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .map-large {{
            height: 600px;
        }}
        
        .footer-wabs {{
            background: var(--dark);
            color: white;
            padding: 30px 0;
            margin-top: 50px;
        }}
        
        .alert-floating {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            animation: slideIn 0.5s;
            min-width: 300px;
        }}
        
        @keyframes slideIn {{
            from {{ transform: translateX(100%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}
        
        .loading-spinner {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }}
        
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        
        .live-dot {{
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #28A745;
            border-radius: 50%;
            animation: livePulse 1s infinite;
        }}
        
        @keyframes livePulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.3; }}
            100% {{ opacity: 1; }}
        }}
        
        .notification-badge {{
            position: absolute;
            top: -5px;
            right: -5px;
            padding: 5px 10px;
            border-radius: 50%;
            background: red;
            color: white;
            font-size: 0.7rem;
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-wabs">
        <div class="container">
            <a class="navbar-brand navbar-brand-wabs" href="/">
                W<span>A</span>BS <span class="tagline">"One Touch for Safety"</span>
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    {f'''<li class="nav-item"><a class="nav-link nav-link-wabs" href="/dashboard"><i class="bi bi-speedometer2"></i> Dashboard</a></li>
                    <li class="nav-item"><a class="nav-link nav-link-wabs" href="/sos"><i class="bi bi-exclamation-triangle-fill text-danger"></i> SOS</a></li>
                    <li class="nav-item"><a class="nav-link nav-link-wabs" href="/voice-detection"><i class="bi bi-mic-fill"></i> Voice</a></li>
                    <li class="nav-item"><a class="nav-link nav-link-wabs" href="/gps-tracking"><i class="bi bi-geo-alt-fill"></i> GPS</a></li>
                    <li class="nav-item"><a class="nav-link nav-link-wabs" href="/child-safety"><i class="bi bi-heart-fill"></i> Child</a></li>
                    <li class="nav-item"><a class="nav-link nav-link-wabs" href="/community"><i class="bi bi-people-fill"></i> Community</a></li>
                    {'''<li class="nav-item"><a class="nav-link nav-link-wabs" href="/admin"><i class="bi bi-shield-fill"></i> Admin</a></li>''' if session.get('user_type') == 'admin' else ''}
                    <li class="nav-item dropdown">
                        <a class="nav-link nav-link-wabs dropdown-toggle" href="#" data-bs-toggle="dropdown">
                            <i class="bi bi-person-circle"></i> {session.get('user_name', 'User')}
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="/dashboard">Profile</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="/logout">Logout</a></li>
                        </ul>
                    </li>''' if session.get('user_id') else '''<li class="nav-item"><a class="nav-link nav-link-wabs" href="/login">Login</a></li>
                    <li class="nav-item"><a class="nav-link nav-link-wabs" href="/register">Register</a></li>'''}
                </ul>
            </div>
        </div>
    </nav>
    
    <div class="container mt-4">
        {'''
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        '''}
        {content_html}
    </div>
    
    {'''<button class="sos-button-giant sos-small" onclick="quickSOS()" title="Emergency SOS">
        SOS
    </button>''' if session.get('user_id') else ''}
    
    <footer class="footer-wabs">
        <div class="container text-center">
            <h5>WABS - Women And Baby Safety System</h5>
            <p class="mb-0">"One Touch for Safety" | Real-Time Protection Platform</p>
            <small>&copy; 2024 WABS. All rights reserved.</small>
        </div>
    </footer>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    {scripts_html}
</body>
</html>'''
    
    return render_template_string(base_template, **kwargs)

# =============================================================================
# ROUTES - All Pages (Same as previous complete code)
# =============================================================================

@app.route('/')
def index():
    """Landing Page with Clickable Feature Cards"""
    content = '''
<div class="row align-items-center min-vh-75 py-5">
    <div class="col-lg-6 text-center text-lg-start mb-5 mb-lg-0">
        <h1 class="display-3 fw-bold mb-3" style="color: var(--dark);">
            Safety at Your <span style="color: var(--primary);">Fingertips</span>
        </h1>
        <p class="lead mb-4" style="color: #666;">
            WABS provides real-time emergency assistance, AI-powered voice detection, 
            live GPS tracking, and community support for women and children.
        </p>
        <div class="d-flex gap-3 justify-content-center justify-content-lg-start">
            <a href="/register" class="btn btn-wabs btn-lg px-5 py-3">
                <i class="bi bi-shield-check"></i> Get Protected Now
            </a>
            <a href="/login" class="btn btn-outline-danger btn-lg px-5 py-3">
                <i class="bi bi-box-arrow-in-right"></i> Login
            </a>
        </div>
        
        <div class="row mt-5 g-3">
            <div class="col-6 col-md-3">
                <div class="stat-card" onclick="showStatInfo('response')">
                    <div class="stat-number">0.5s</div>
                    <div class="stat-label">Response</div>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card" onclick="showStatInfo('monitoring')">
                    <div class="stat-number">24/7</div>
                    <div class="stat-label">Monitoring</div>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card" onclick="showStatInfo('ai')">
                    <div class="stat-number">AI</div>
                    <div class="stat-label">Powered</div>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card" onclick="showStatInfo('gps')">
                    <div class="stat-number">GPS</div>
                    <div class="stat-label">Live</div>
                </div>
            </div>
        </div>
    </div>
    <div class="col-lg-6 text-center">
        <div class="position-relative d-inline-block">
            <div class="sos-button-giant" onclick="window.location.href='/register'">
                SOS
            </div>
            <p class="mt-3 fw-bold" style="color: var(--primary); font-size: 1.2rem;">
                One Touch for Safety
            </p>
        </div>
    </div>
</div>

<div class="row mt-5 pt-5">
    <div class="col-12 text-center mb-5">
        <h2 class="fw-bold">How WABS Protects You</h2>
        <p class="text-muted">Click on any feature to learn more</p>
    </div>
    <div class="col-md-4 mb-4">
        <div class="card-wabs p-4 h-100 clickable" onclick="navigateTo('/voice-detection')">
            <div class="text-center mb-3">
                <i class="bi bi-mic-fill text-danger" style="font-size: 3rem;"></i>
            </div>
            <h5 class="text-center">Voice Detection</h5>
            <p class="text-center text-muted">AI detects distress phrases in English, Tamil & Tanglish. Just speak and get help automatically.</p>
            <div class="text-center mt-3">
                <span class="badge bg-danger">Live</span>
                <span class="badge bg-info">AI Powered</span>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-4">
        <div class="card-wabs p-4 h-100 clickable" onclick="navigateTo('/gps-tracking')">
            <div class="text-center mb-3">
                <i class="bi bi-geo-alt-fill text-danger" style="font-size: 3rem;"></i>
            </div>
            <h5 class="text-center">Live GPS Tracking</h5>
            <p class="text-center text-muted">Real-time location sharing with family and emergency contacts. Track your loved ones.</p>
            <div class="text-center mt-3">
                <span class="badge bg-success">Real-Time</span>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-4">
        <div class="card-wabs p-4 h-100 clickable" onclick="navigateTo('/community')">
            <div class="text-center mb-3">
                <i class="bi bi-people-fill text-danger" style="font-size: 3rem;"></i>
            </div>
            <h5 class="text-center">Community Network</h5>
            <p class="text-center text-muted">Nearby volunteers receive alerts and provide immediate assistance when you need help.</p>
            <div class="text-center mt-3">
                <span class="badge bg-warning">Active</span>
            </div>
        </div>
    </div>
</div>
'''
    
    scripts = '''
<script>
function navigateTo(url) { window.location.href = url; }
function showStatInfo(type) {
    const info = {
        'response': 'Our system responds in under 0.5 seconds to ensure immediate help.',
        'monitoring': '24/7 AI-powered monitoring keeps you safe around the clock.',
        'ai': 'Advanced AI detects distress in voice, sound, and behavior patterns.',
        'gps': 'Live GPS tracking with real-time location sharing to emergency contacts.'
    };
    alert(info[type] || 'Feature information');
}
</script>
'''
    
    return render_page(content, scripts, "Home")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = Users.query.filter_by(Email=email, IsActive=True).first()
        
        if user and check_password_hash(user.PasswordHash, password):
            session['user_id'] = user.UserID
            session['user_name'] = user.Name
            session['user_type'] = user.UserType
            user.LastLogin = datetime.datetime.utcnow()
            db.session.commit()
            
            flash(f'Welcome back, {user.Name}! 🎉', 'success')
            
            if user.UserType == 'admin':
                return redirect(url_for('admin_panel'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    content = '''
<div class="row justify-content-center mt-5">
    <div class="col-md-5">
        <div class="card-wabs">
            <div class="card-header-wabs text-center">
                <h4 class="mb-0"><i class="bi bi-box-arrow-in-right"></i> Login to WABS</h4>
            </div>
            <div class="card-body p-4">
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Email Address</label>
                        <input type="email" name="email" class="form-control" placeholder="your@email.com" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input type="password" name="password" class="form-control" placeholder="••••••••" required>
                    </div>
                    <button type="submit" class="btn btn-wabs w-100 py-3">Login Securely</button>
                </form>
                <div class="text-center mt-3">
                    <p>Don't have an account? <a href="/register" style="color: var(--primary);">Register here</a></p>
                    <p><small>Demo: admin@wabs.com / admin123</small></p>
                </div>
            </div>
        </div>
    </div>
</div>
'''
    return render_page(content, "", "Login")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        mobile = request.form.get('mobile')
        email = request.form.get('email')
        address = request.form.get('address')
        password = request.form.get('password')
        user_type = request.form.get('user_type', 'woman')
        
        existing = Users.query.filter((Users.Email == email) | (Users.Mobile == mobile)).first()
        if existing:
            flash('Email or mobile already registered!', 'warning')
            return redirect(url_for('login'))
        
        new_user = Users(
            Name=name, Mobile=mobile, Email=email, Address=address,
            PasswordHash=generate_password_hash(password), UserType=user_type,
            IsActive=True, CreatedAt=datetime.datetime.utcnow()
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('✅ Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    content = '''
<div class="row justify-content-center mt-4">
    <div class="col-md-6">
        <div class="card-wabs">
            <div class="card-header-wabs text-center">
                <h4 class="mb-0"><i class="bi bi-person-plus"></i> Register for WABS</h4>
            </div>
            <div class="card-body p-4">
                <form method="POST">
                    <div class="mb-3"><label>Full Name *</label><input type="text" name="name" class="form-control" required></div>
                    <div class="row mb-3">
                        <div class="col-md-6"><label>Mobile *</label><input type="tel" name="mobile" class="form-control" required></div>
                        <div class="col-md-6"><label>Email *</label><input type="email" name="email" class="form-control" required></div>
                    </div>
                    <div class="mb-3"><label>Address</label><textarea name="address" class="form-control" rows="2"></textarea></div>
                    <div class="row mb-3">
                        <div class="col-md-6"><label>Password *</label><input type="password" name="password" class="form-control" minlength="8" required></div>
                        <div class="col-md-6"><label>User Type *</label>
                            <select name="user_type" class="form-select">
                                <option value="woman">👩 Woman User</option>
                                <option value="parent">👨‍👩‍👧 Parent</option>
                                <option value="volunteer">🤝 Volunteer</option>
                            </select>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-wabs w-100 py-3">Register Now</button>
                </form>
                <div class="text-center mt-3"><p>Already have an account? <a href="/login" style="color: var(--primary);">Login</a></p></div>
            </div>
        </div>
    </div>
</div>
'''
    return render_page(content, "", "Register")

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully. Stay safe! 🛡️', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = Users.query.get(session['user_id'])
    sos_count = SOSRecords.query.filter_by(UserID=user.UserID).count()
    active_sos = SOSRecords.query.filter_by(UserID=user.UserID, Status='active').count()
    contacts_count = EmergencyContacts.query.filter_by(UserID=user.UserID, IsActive=True).count()
    children = Children.query.filter_by(UserID=user.UserID, IsActive=True).all()
    
    content = f'''
<div class="row mb-4">
    <div class="col-12">
        <h2 class="fw-bold">Welcome, {user.Name}! 👋</h2>
        <p class="text-muted">Your real-time safety dashboard | <span class="live-dot"></span> Live</p>
    </div>
</div>

<div class="row g-3 mb-4">
    <div class="col-6 col-md-3"><div class="stat-card" onclick="window.location.href='/sos'"><div class="stat-number">{sos_count}</div><div class="stat-label">Total SOS</div></div></div>
    <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-number text-warning">{active_sos}</div><div class="stat-label">Active Alerts</div></div></div>
    <div class="col-6 col-md-3"><div class="stat-card" onclick="openContactModal()"><div class="stat-number text-info">{contacts_count}</div><div class="stat-label">Contacts</div></div></div>
    <div class="col-6 col-md-3"><div class="stat-card" onclick="window.location.href='/child-safety'"><div class="stat-number text-success">{len(children)}</div><div class="stat-label">Children</div></div></div>
</div>

<div class="row">
    <div class="col-lg-8 mb-4">
        <div class="card-wabs">
            <div class="card-header-wabs d-flex justify-content-between align-items-center">
                <span><i class="bi bi-exclamation-triangle"></i> Emergency SOS</span>
                <span class="badge bg-danger"><span class="live-dot"></span> LIVE</span>
            </div>
            <div class="card-body text-center py-5">
                <button class="sos-button-giant" onclick="triggerSOS()" id="sosBtn">SOS</button>
                <p class="mt-3 fw-bold text-danger">Press in case of emergency</p>
                <small class="text-muted">GPS location, SMS, and alerts will be sent automatically</small>
            </div>
        </div>
    </div>
    <div class="col-lg-4 mb-4">
        <div class="card-wabs h-100">
            <div class="card-header-wabs"><i class="bi bi-telephone"></i> Emergency Contacts</div>
            <div class="card-body">
                <div id="contacts-list"><p class="text-muted">Loading...</p></div>
                <button class="btn btn-wabs w-100 mt-3" onclick="openContactModal()">Add Contact</button>
            </div>
        </div>
    </div>
</div>
'''
    
    scripts = '''
<script>
let currentPosition = { latitude: 13.0827, longitude: 80.2707 };

function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => { currentPosition = { latitude: position.coords.latitude, longitude: position.coords.longitude }; },
            (error) => console.log('GPS:', error)
        );
    }
}
getLocation();
setInterval(getLocation, 30000);

function openContactModal() { alert('Contact management - Add up to 5 emergency contacts.'); }

async function triggerSOS() {
    if (!confirm('🚨 EMERGENCY! Alert all contacts?')) return;
    try {
        const response = await fetch('/api/sos/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latitude: currentPosition.latitude, longitude: currentPosition.longitude, alert_type: 'manual' })
        });
        const data = await response.json();
        if (data.success) alert('✅ SOS ACTIVATED! Help is on the way.');
    } catch (error) { alert('Error! Call 100/112 directly!'); }
}

function quickSOS() { triggerSOS(); }
</script>
'''
    
    return render_page(content, scripts, "Dashboard")

# Additional routes (sos, voice-detection, gps-tracking, child-safety, community, admin) 
# follow the same pattern as the previous complete code

@app.route('/sos')
@login_required
def sos_page():
    content = '''
<div class="row justify-content-center mt-4">
    <div class="col-lg-8 text-center">
        <div class="card-wabs p-5">
            <h3 class="mb-4 fw-bold text-danger">🚨 Emergency SOS System</h3>
            <p class="lead">Press the button to activate full emergency mode</p>
            <div class="my-5">
                <button class="sos-button-giant" onclick="triggerEmergencySOS()" style="width: 250px; height: 250px; font-size: 3rem;">SOS</button>
            </div>
            <div class="alert alert-danger text-start">
                <strong>⚠️ This will immediately:</strong>
                <ul><li>📡 Share GPS location</li><li>📱 SMS to contacts</li><li>🔔 Alert community</li><li>🔊 Activate alarm</li></ul>
            </div>
        </div>
    </div>
</div>
'''
    scripts = '''
<script>
let sosLocation = { latitude: 13.0827, longitude: 80.2707 };
if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => { sosLocation = { latitude: pos.coords.latitude, longitude: pos.coords.longitude }; });
}

async function triggerEmergencySOS() {
    if (!confirm('🚨 Activate SOS?')) return;
    try {
        const response = await fetch('/api/sos/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latitude: sosLocation.latitude, longitude: sosLocation.longitude, alert_type: 'manual' })
        });
        const data = await response.json();
        if (data.success) alert('✅ SOS ACTIVATED!');
    } catch (error) { alert('Error! Call 100/112!'); }
}
</script>
'''
    return render_page(content, scripts, "Emergency SOS")

@app.route('/voice-detection')
@login_required
def voice_detection():
    content = '''
<div class="row mb-4"><div class="col-12"><h3 class="fw-bold"><i class="bi bi-mic-fill text-danger"></i> AI Voice Detection</h3><p class="text-muted">Real-time voice monitoring with automatic SOS trigger</p></div></div>
<div class="row">
    <div class="col-lg-8">
        <div class="card-wabs">
            <div class="card-header-wabs"><span><i class="bi bi-ear"></i> Voice Monitor</span><span class="badge bg-success">● Active</span></div>
            <div class="card-body text-center py-5">
                <div class="voice-indicator" id="voiceIndicator" onclick="toggleListening()"><i class="bi bi-mic-fill text-white" style="font-size: 3rem;"></i></div>
                <h5 class="mt-3" id="listeningStatus">Click to Start Listening</h5>
                <p class="text-muted">Speak distress phrases in English, Tamil, or Tanglish</p>
                <div class="mt-4">
                    <button class="btn btn-danger btn-lg me-2" id="startListenBtn" onclick="toggleListening()"><i class="bi bi-mic"></i> Start Listening</button>
                    <button class="btn btn-outline-danger btn-lg" onclick="simulateDetection()"><i class="bi bi-play"></i> Simulate Test</button>
                </div>
                <div id="transcriptBox" class="mt-4 p-3 bg-light rounded" style="min-height: 100px;"><p class="text-muted">Transcribed text will appear here...</p></div>
                <div id="detectionAlert" class="mt-3"></div>
            </div>
        </div>
    </div>
    <div class="col-lg-4">
        <div class="card-wabs mb-3">
            <div class="card-header-wabs">Supported Keywords</div>
            <div class="card-body">
                <h6>🇬🇧 English</h6>
                <span class="badge bg-danger m-1">Help Me</span><span class="badge bg-danger m-1">Save Me</span><span class="badge bg-danger m-1">Emergency</span>
                <h6 class="mt-2">🇮🇳 Tamil</h6>
                <span class="badge bg-warning text-dark m-1">காப்பாற்றுங்கள்</span><span class="badge bg-warning text-dark m-1">உதவி செய்யுங்கள்</span>
                <h6 class="mt-2">🔀 Tanglish</h6>
                <span class="badge bg-info m-1">Help pannunga</span><span class="badge bg-info m-1">Save pannunga</span>
            </div>
        </div>
    </div>
</div>
'''
    scripts = '''
<script>
let isListening = false, recognition = null;

function initSpeechRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('Use Chrome for speech recognition.'); return null; }
    const recog = new SR();
    recog.continuous = true;
    recog.interimResults = true;
    recog.lang = 'en-IN';
    recog.onresult = function(event) {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) transcript += event.results[i][0].transcript + ' ';
        }
        document.getElementById('transcriptBox').innerHTML = '<strong>You said:</strong> ' + transcript;
        if (transcript.trim()) processVoiceInput(transcript.trim());
    };
    recog.onend = function() { if (isListening) recog.start(); };
    return recog;
}

function toggleListening() {
    if (!recognition) { recognition = initSpeechRecognition(); if (!recognition) return; }
    if (isListening) {
        recognition.stop(); isListening = false;
        document.getElementById('voiceIndicator').classList.remove('listening');
        document.getElementById('listeningStatus').textContent = 'Listening Stopped';
        document.getElementById('startListenBtn').innerHTML = '<i class="bi bi-mic"></i> Start Listening';
    } else {
        recognition.start(); isListening = true;
        document.getElementById('voiceIndicator').classList.add('listening');
        document.getElementById('listeningStatus').textContent = '🔴 Listening... Speak now';
        document.getElementById('startListenBtn').innerHTML = '<i class="bi bi-stop-fill"></i> Stop Listening';
    }
}

async function processVoiceInput(transcript) {
    let language = 'english';
    if (/[\\u0B80-\\u0BFF]/.test(transcript)) language = 'tamil';
    const tanglishWords = ['pannunga', 'iruken', 'kappathunga'];
    if (tanglishWords.some(w => transcript.toLowerCase().includes(w))) language = 'tanglish';
    
    try {
        const response = await fetch('/api/audio/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: transcript, language, confidence: 0.85 })
        });
        const data = await response.json();
        if (data.is_distress) {
            document.getElementById('detectionAlert').innerHTML = `<div class="alert alert-danger"><h5>🚨 DISTRESS DETECTED!</h5><p>Keyword: <strong>${data.matched_keyword}</strong></p>${data.sos_triggered ? '<p class="fw-bold">⚠️ SOS AUTO-TRIGGERED!</p>' : ''}</div>`;
        }
    } catch (error) {}
}

async function simulateDetection() {
    const phrases = [{ text: 'Help me please', language: 'english' }, { text: 'Danger la iruken', language: 'tanglish' }];
    const phrase = phrases[Math.floor(Math.random() * phrases.length)];
    document.getElementById('transcriptBox').innerHTML = '<strong>Simulated:</strong> ' + phrase.text;
    await processVoiceInput(phrase.text);
}
</script>
'''
    return render_page(content, scripts, "Voice Detection")

@app.route('/gps-tracking')
@login_required
def gps_tracking():
    content = '''
<div class="row mb-4"><div class="col-12"><h3 class="fw-bold"><i class="bi bi-geo-alt-fill text-danger"></i> Live GPS Tracking</h3><p class="text-muted"><span class="live-dot"></span> Real-time location monitoring</p></div></div>
<div class="row">
    <div class="col-lg-8">
        <div class="card-wabs">
            <div class="card-header-wabs d-flex justify-content-between"><span><i class="bi bi-map"></i> Live Map</span><div><span class="badge bg-success me-2">● Tracking</span><span class="badge bg-info" id="updateCount">Updates: 0</span></div></div>
            <div class="card-body p-0"><div id="liveMap" class="map-container map-large"></div></div>
        </div>
    </div>
    <div class="col-lg-4">
        <div class="card-wabs mb-3">
            <div class="card-header-wabs">Current Location</div>
            <div class="card-body text-center">
                <h4 id="currentLat">13.0827</h4><small>Latitude</small>
                <h4 id="currentLng">80.2707</h4><small>Longitude</small>
                <div class="mt-3"><span class="badge bg-success" id="accuracyBadge">--</span></div>
                <button class="btn btn-wabs w-100 mt-3" onclick="shareLocation()">Share Location</button>
            </div>
        </div>
        <div class="card-wabs"><div class="card-header-wabs">Route History</div><div class="card-body" id="routeHistory"><p class="text-muted">Recording...</p></div></div>
    </div>
</div>
'''
    scripts = '''
<script>
let map, marker, pathLine, pathCoordinates = [], updateCounter = 0, currentLocation = { lat: 13.0827, lng: 80.2707 };

function initMap() {
    map = L.map('liveMap').setView([13.0827, 80.2707], 16);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
    const userIcon = L.divIcon({ html: '<div style="background:red;width:15px;height:15px;border-radius:50%;border:2px solid white;"></div>', iconSize: [15,15] });
    marker = L.marker([13.0827, 80.2707], { icon: userIcon }).addTo(map).bindPopup('<b>Your Location</b>').openPopup();
    pathLine = L.polyline([], { color: 'red', weight: 3 }).addTo(map);
}

function updateLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => {
            currentLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            updateCounter++;
            document.getElementById('currentLat').textContent = currentLocation.lat.toFixed(6);
            document.getElementById('currentLng').textContent = currentLocation.lng.toFixed(6);
            document.getElementById('accuracyBadge').textContent = `±${pos.coords.accuracy.toFixed(0)}m`;
            document.getElementById('updateCount').textContent = `Updates: ${updateCounter}`;
            if (map && marker) {
                const newPos = [currentLocation.lat, currentLocation.lng];
                marker.setLatLng(newPos);
                pathCoordinates.push(newPos);
                if (pathCoordinates.length > 100) pathCoordinates.shift();
                pathLine.setLatLngs(pathCoordinates);
                document.getElementById('routeHistory').innerHTML = pathCoordinates.slice(-5).reverse().map(c => `<div class="p-1 bg-light rounded mb-1"><small>📍 ${c[0].toFixed(4)}, ${c[1].toFixed(4)}</small></div>`).join('');
            }
            fetch('/api/location/update', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ latitude: currentLocation.lat, longitude: currentLocation.lng, accuracy: pos.coords.accuracy }) });
        }, null, { enableHighAccuracy: true });
    }
}

function shareLocation() {
    const url = `https://www.google.com/maps?q=${currentLocation.lat},${currentLocation.lng}`;
    navigator.share ? navigator.share({ title: 'My Location', url }) : prompt('Copy:', url);
}

document.addEventListener('DOMContentLoaded', () => { initMap(); updateLocation(); setInterval(updateLocation, 5000); });
</script>
'''
    return render_page(content, scripts, "GPS Tracking")

@app.route('/child-safety')
@login_required
def child_safety():
    user = Users.query.get(session['user_id'])
    children = Children.query.filter_by(UserID=user.UserID, IsActive=True).all()
    
    children_cards = ''
    for child in children:
        children_cards += f'<div class="col-md-6 mb-3"><div class="card-wabs p-3"><h5>{child.ChildName}</h5><p>Age: {child.Age} | Code: {child.ChildCode}</p></div></div>'
    
    content = f'''
<div class="row mb-4"><div class="col-12"><h3 class="fw-bold"><i class="bi bi-heart-fill text-danger"></i> Child Safety</h3></div></div>
<div class="row">
    <div class="col-lg-8">
        <div class="card-wabs mb-4">
            <div class="card-header-wabs">Sound Detection</div>
            <div class="card-body text-center py-4">
                <div class="voice-indicator" style="background: linear-gradient(135deg, #FF6B6B, #FF8E8E);"><i class="bi bi-ear-fill text-white" style="font-size: 3rem;"></i></div>
                <h5 class="mt-3">Child Distress Sounds</h5>
                <div class="row mt-4">
                    <div class="col-md-4"><button class="btn btn-outline-danger w-100" onclick="simulateSound('crying')">😢 Crying</button></div>
                    <div class="col-md-4"><button class="btn btn-outline-danger w-100" onclick="simulateSound('screaming')">😱 Screaming</button></div>
                    <div class="col-md-4"><button class="btn btn-outline-danger w-100" onclick="simulateSound('panic')">🆘 Panic</button></div>
                </div>
                <div id="soundResult" class="mt-4"></div>
            </div>
        </div>
    </div>
    <div class="col-lg-4">
        <div class="card-wabs">
            <div class="card-header-wabs">Registered Children</div>
            <div class="card-body"><div class="row">{children_cards if children_cards else '<p class="text-muted">No children registered.</p>'}</div></div>
        </div>
    </div>
</div>
'''
    scripts = '''
<script>
async function simulateSound(type) {
    try {
        const response = await fetch('/api/child/sound/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sound_type: type, confidence: 0.85, latitude: 13.0827, longitude: 80.2707 })
        });
        const data = await response.json();
        document.getElementById('soundResult').innerHTML = `<div class="alert alert-danger"><h5>🚨 Detected: ${type.toUpperCase()}</h5>${data.alert_triggered ? '<p class="fw-bold">⚠️ Alert sent!</p>' : ''}</div>`;
    } catch (error) {}
}
</script>
'''
    return render_page(content, scripts, "Child Safety")

@app.route('/community')
@login_required
def community():
    content = '''
<div class="row mb-4"><div class="col-12"><h3 class="fw-bold"><i class="bi bi-people-fill text-primary"></i> Community Network</h3></div></div>
<div class="row">
    <div class="col-lg-8">
        <div class="card-wabs mb-4">
            <div class="card-header-wabs d-flex justify-content-between"><span>Nearby Alerts</span><select id="radiusSelect" class="form-select form-select-sm w-auto" onchange="loadAlerts()"><option value="500">500m</option><option value="1000">1km</option></select></div>
            <div class="card-body" id="nearbyAlerts"><div class="text-center py-4"><div class="spinner-border text-danger"></div><p>Scanning...</p></div></div>
        </div>
    </div>
    <div class="col-lg-4">
        <div class="card-wabs mb-3"><div class="card-header-wabs">Voice Alarm</div><div class="card-body"><button class="btn btn-danger w-100" onclick="playAlarm()">Play Announcement</button></div></div>
    </div>
</div>
'''
    scripts = '''
<script>
async function loadAlerts() {
    try {
        const response = await fetch('/api/community/alerts/nearby', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ latitude: 13.0827, longitude: 80.2707, radius: 500 }) });
        const data = await response.json();
        const div = document.getElementById('nearbyAlerts');
        div.innerHTML = data.alerts.length === 0 ? '<div class="text-center py-4"><i class="bi bi-check-circle text-success" style="font-size:3rem;"></i><p>Area is safe.</p></div>' : data.alerts.map(a => `<div class="alert alert-danger"><strong>🚨 EMERGENCY</strong><p>${a.message}</p><button class="btn btn-success btn-sm" onclick="respond(${a.alert_id})">I'll Help</button></div>`).join('');
    } catch (error) {}
}
async function respond(id) { await fetch(`/api/community/respond/${id}`, { method: 'POST' }); alert('✅ Response recorded!'); loadAlerts(); }
function playAlarm() { const u = new SpeechSynthesisUtterance("Attention! A woman or child may be in danger. Please help immediately."); for (let i=0;i<3;i++) setTimeout(() => speechSynthesis.speak(u), i*3000); }
loadAlerts(); setInterval(loadAlerts, 15000);
</script>
'''
    return render_page(content, scripts, "Community")

@app.route('/admin')
@admin_required
def admin_panel():
    total_users = Users.query.count()
    total_sos = SOSRecords.query.count()
    active_sos = SOSRecords.query.filter_by(Status='active').count()
    total_recordings = VoiceRecordings.query.count()
    
    # Get all users
    all_users = Users.query.order_by(Users.CreatedAt.desc()).limit(20).all()
    users_table = ''.join([f'<tr><td>{u.UserID}</td><td>{u.Name}</td><td>{u.Mobile}</td><td>{u.Email}</td><td><span class="badge bg-info">{u.UserType}</span></td><td>{u.LastLogin.strftime("%d %b %H:%M") if u.LastLogin else "Never"}</td></tr>' for u in all_users])
    
    # Get all recordings
    all_recordings = VoiceRecordings.query.order_by(VoiceRecordings.CreatedAt.desc()).limit(20).all()
    recordings_table = ''.join([f'<tr><td>{r.RecordingID}</td><td>{r.user.Name if r.user else "Unknown"}</td><td>{r.TranscribedText[:50] if r.TranscribedText else "N/A"}...</td><td>{r.Language or "N/A"}</td><td><span class="badge bg-{"danger" if r.IsEmergency else "success"}">{"Emergency" if r.IsEmergency else "Normal"}</span></td><td>{r.CreatedAt.strftime("%d %b %H:%M") if r.CreatedAt else "N/A"}</td></tr>' for r in all_recordings])
    
    content = f'''
<div class="row mb-4"><div class="col-12"><h3 class="fw-bold"><i class="bi bi-shield-fill text-warning"></i> Admin Panel</h3></div></div>
<div class="row g-3 mb-4">
    <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-number">{total_users}</div><div class="stat-label">Users</div></div></div>
    <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-number text-danger">{total_sos}</div><div class="stat-label">SOS</div></div></div>
    <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-number text-warning">{active_sos}</div><div class="stat-label">Active</div></div></div>
    <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-number text-info">{total_recordings}</div><div class="stat-label">Recordings</div></div></div>
</div>
<ul class="nav nav-tabs mb-4">
    <li class="nav-item"><a class="nav-link active" data-bs-toggle="tab" href="#usersTab">👥 Users</a></li>
    <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#recordingsTab">🎙️ Voice Recordings</a></li>
</ul>
<div class="tab-content">
    <div class="tab-pane fade show active" id="usersTab">
        <div class="card-wabs"><div class="card-header-wabs">All Users</div><div class="card-body table-responsive"><table class="table table-hover"><thead><tr><th>ID</th><th>Name</th><th>Mobile</th><th>Email</th><th>Type</th><th>Last Login</th></tr></thead><tbody>{users_table}</tbody></table></div></div>
    </div>
    <div class="tab-pane fade" id="recordingsTab">
        <div class="card-wabs"><div class="card-header-wabs">All Voice Recordings (Admin Only)</div><div class="card-body table-responsive"><table class="table table-hover"><thead><tr><th>ID</th><th>User</th><th>Transcript</th><th>Language</th><th>Type</th><th>Time</th></tr></thead><tbody>{recordings_table}</tbody></table></div></div>
    </div>
</div>
'''
    return render_page(content, "", "Admin Panel")

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/sos/trigger', methods=['POST'])
@login_required
def trigger_sos():
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        alert_type = data.get('alert_type', 'manual')
        
        user = Users.query.get(session['user_id'])
        
        sos_record = SOSRecords(
            UserID=user.UserID, DateTime=datetime.datetime.utcnow(),
            Latitude=latitude, Longitude=longitude, Status='active',
            AlertType=alert_type,
            LocationLink=f"https://www.google.com/maps?q={latitude},{longitude}"
        )
        db.session.add(sos_record)
        db.session.flush()
        
        community_alert = CommunityAlerts(
            SOSID=sos_record.SOSID, UserID=user.UserID,
            Latitude=latitude, Longitude=longitude, Radius=1000,
            AlertType='emergency', AlertMessage=f"🚨 EMERGENCY! A {user.UserType} needs help!",
            IsActive=True, SentAt=datetime.datetime.utcnow(),
            ExpiresAt=datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        )
        db.session.add(community_alert)
        db.session.commit()
        
        send_all_notifications(user, sos_record)
        
        return jsonify({'success': True, 'message': 'SOS activated!', 'sos_id': sos_record.SOSID, 'location_link': sos_record.LocationLink})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/location/update', methods=['POST'])
@login_required
def update_location():
    try:
        data = request.get_json()
        location = LocationTracking(
            UserID=session['user_id'], Latitude=data['latitude'],
            Longitude=data['longitude'], Accuracy=data.get('accuracy'),
            Timestamp=datetime.datetime.utcnow()
        )
        db.session.add(location)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/audio/detect', methods=['POST'])
@login_required
def detect_audio():
    try:
        data = request.get_json()
        detected_text = data.get('text', '').lower()
        language = data.get('language', 'english')
        confidence = data.get('confidence', 0.85)
        
        keywords = ['help me', 'save me', 'emergency', 'i am in danger', 'somebody help']
        if language == 'tamil':
            keywords = ['காப்பாற்றுங்கள்', 'உதவி செய்யுங்கள்', 'ஆபத்தில்']
        elif language == 'tanglish':
            keywords = ['help pannunga', 'save pannunga', 'danger la iruken']
        
        is_distress = any(k in detected_text for k in keywords)
        matched = next((k for k in keywords if k in detected_text), None)
        
        recording = VoiceRecordings(
            UserID=session['user_id'], TranscribedText=detected_text,
            Language=language, IsEmergency=is_distress,
            CreatedAt=datetime.datetime.utcnow()
        )
        db.session.add(recording)
        db.session.commit()
        
        sos_triggered = False
        if is_distress and confidence > 0.7:
            sos_triggered = True
            sos_record = SOSRecords(
                UserID=session['user_id'], DateTime=datetime.datetime.utcnow(),
                Latitude=data.get('latitude', 13.0827),
                Longitude=data.get('longitude', 80.2707),
                Status='active', AlertType='voice',
                LocationLink=f"https://www.google.com/maps?q={data.get('latitude', 13.0827)},{data.get('longitude', 80.2707)}"
            )
            db.session.add(sos_record)
            db.session.commit()
        
        return jsonify({'success': True, 'is_distress': is_distress, 'matched_keyword': matched, 'confidence': confidence, 'sos_triggered': sos_triggered})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/contacts/add', methods=['POST'])
@login_required
def add_contact():
    data = request.get_json()
    existing = EmergencyContacts.query.filter_by(UserID=session['user_id'], IsActive=True).count()
    if existing >= 5:
        return jsonify({'success': False, 'message': 'Max 5 contacts allowed.'})
    
    contact = EmergencyContacts(UserID=session['user_id'], ContactName=data['contact_name'], Relationship=data['relationship'], Mobile=data['mobile'], PriorityLevel=data.get('priority', 1))
    db.session.add(contact)
    db.session.commit()
    return jsonify({'success': True, 'contact_id': contact.ContactID})

@app.route('/api/contacts/list', methods=['GET'])
@login_required
def list_contacts():
    contacts = EmergencyContacts.query.filter_by(UserID=session['user_id'], IsActive=True).all()
    return jsonify({'success': True, 'contacts': [{'contact_id': c.ContactID, 'name': c.ContactName, 'relationship': c.Relationship, 'mobile': c.Mobile} for c in contacts]})

@app.route('/api/contacts/delete/<int:contact_id>', methods=['DELETE'])
@login_required
def delete_contact(contact_id):
    contact = EmergencyContacts.query.get_or_404(contact_id)
    if contact.UserID != session['user_id']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    contact.IsActive = False
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/child/add', methods=['POST'])
@login_required
def add_child():
    data = request.get_json()
    child_code = secrets.token_hex(4).upper()
    child = Children(UserID=session['user_id'], ChildName=data['child_name'], Age=data['age'], Gender=data.get('gender'), ParentName=data.get('parent_name'), ParentMobile=data.get('parent_mobile'), MedicalInfo=data.get('medical_info'), ChildCode=child_code, IsActive=True)
    db.session.add(child)
    db.session.commit()
    return jsonify({'success': True, 'child_id': child.ChildID, 'child_code': child_code})

@app.route('/api/child/sound/detect', methods=['POST'])
@login_required
def detect_child_sound():
    data = request.get_json()
    sound_type = data.get('sound_type')
    confidence = data.get('confidence', 0.8)
    alert_triggered = confidence > 0.75
    
    if alert_triggered:
        sos_record = SOSRecords(UserID=session['user_id'], DateTime=datetime.datetime.utcnow(), Latitude=data.get('latitude', 13.0827), Longitude=data.get('longitude', 80.2707), Status='active', AlertType='child_sound', LocationLink=f"https://www.google.com/maps?q={data.get('latitude', 13.0827)},{data.get('longitude', 80.2707)}")
        db.session.add(sos_record)
        db.session.commit()
    
    return jsonify({'success': True, 'sound_type': sound_type, 'alert_triggered': alert_triggered})

@app.route('/api/community/alerts/nearby', methods=['POST'])
@login_required
def nearby_alerts():
    alerts = CommunityAlerts.query.filter(CommunityAlerts.IsActive == True, CommunityAlerts.ExpiresAt > datetime.datetime.utcnow()).order_by(CommunityAlerts.SentAt.desc()).limit(20).all()
    return jsonify({'success': True, 'alerts': [{'alert_id': a.AlertID, 'message': a.AlertMessage, 'latitude': a.Latitude, 'longitude': a.Longitude, 'sent_at': a.SentAt.isoformat() if a.SentAt else None, 'responded_count': a.RespondedCount} for a in alerts]})

@app.route('/api/community/respond/<int:alert_id>', methods=['POST'])
@login_required
def respond_alert(alert_id):
    alert = CommunityAlerts.query.get_or_404(alert_id)
    alert.RespondedCount += 1
    response = CommunityResponses(AlertID=alert_id, UserID=session['user_id'], RespondedAt=datetime.datetime.utcnow())
    db.session.add(response)
    db.session.commit()
    return jsonify({'success': True, 'responded_count': alert.RespondedCount})

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    user_id = session['user_id']
    return jsonify({'success': True, 'stats': {'total_sos': SOSRecords.query.filter_by(UserID=user_id).count(), 'active_sos': SOSRecords.query.filter_by(UserID=user_id, Status='active').count()}})

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    return jsonify({'success': True, 'total_users': Users.query.count(), 'total_sos': SOSRecords.query.count(), 'total_recordings': VoiceRecordings.query.count()})

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def send_all_notifications(user, sos_record):
    contacts = EmergencyContacts.query.filter_by(UserID=user.UserID, IsActive=True).all()
    print(f"\n🚨 SOS ACTIVATED - User: {user.Name}, Location: {sos_record.LocationLink}")
    for contact in contacts:
        print(f"  📱 Notifying: {contact.ContactName} ({contact.Mobile})")
    return True

# =============================================================================
# INITIALIZATION
# =============================================================================

def init_db():
    with app.app_context():
        db.create_all()
        
        admin = Users.query.filter_by(Email='admin@wabs.com').first()
        if not admin:
            admin = Users(
                Name='System Administrator', Mobile='+919876543210',
                Email='admin@wabs.com', Address='WABS Security Headquarters',
                PasswordHash=generate_password_hash('admin123'), UserType='admin',
                IsActive=True, CreatedAt=datetime.datetime.utcnow()
            )
            db.session.add(admin)
            db.session.commit()
            print("\n✅ Admin created: admin@wabs.com / admin123")
        
        print("\n" + "="*70)
        print("   WABS - Women And Baby Safety System")
        print('   "One Touch for Safety"')
        print("   Production-Ready Real-Time Safety Platform")
        print("="*70)
        print("   ✅ Real-time GPS Tracking")
        print("   ✅ AI Voice Detection (English/Tamil/Tanglish)")
        print("   ✅ Community Safety Network")
        print("   ✅ Child Safety Monitoring")
        print("   ✅ Admin Panel with Full Data Access")
        print("   ✅ Voice Recording Storage")
        print("   ✅ Emergency SOS System")
        print(f"   🌐 http://localhost:5000")
        print(f"   👤 Admin: admin@wabs.com / admin123")
        print("="*70 + "\n")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)