# Flask Educational Application

## Overview
This is a Flask educational application for managing student activities and lesson plans. It was originally designed for educational institutions to manage courses, assignments, and student attendance.

## Current Status
- ✅ Flask server is running successfully on port 5000
- ✅ Basic web interface is working
- ⚠️ Database features temporarily disabled (PostgreSQL integration in progress)
- ⚠️ Authentication features temporarily disabled (dependency issues to resolve)

## Project Structure
- `app.py` - Main Flask application (full version with database features)
- `simple_app.py` - Simplified version currently running
- `database.py` - Database operations and models
- `models.py` - SQLAlchemy database models
- `templates/` - HTML templates for the web interface
- `static/` - Static assets (images, PDFs)
- `requirements.txt` - Python dependencies

## Dependencies Status
- Flask ✅ Working
- Basic templating ✅ Working  
- Database dependencies ⚠️ Need installation (psycopg2-binary, sqlalchemy, flask-sqlalchemy)
- Authentication ⚠️ Need installation (flask-bcrypt)
- File processing ⚠️ Need installation (weasyprint, cloudinary)

## Database Setup
The application is configured to use PostgreSQL with the following environment variables:
- DATABASE_URL (configured)
- PGDATABASE, PGHOST, PGPORT, PGUSER, PGPASSWORD (configured)

## Next Steps for Full Functionality
1. Install missing Python dependencies
2. Re-enable database connections
3. Re-enable authentication features
4. Set up API keys for file upload services
5. Test all educational workflows

## Running the Application
The Flask server runs on port 5000 and is accessible through the webview interface.

## User Preferences
- Database: PostgreSQL (Replit managed)
- Authentication: Flask-Bcrypt for password hashing
- File Storage: Cloudinary for PDF uploads
- Session Management: Flask sessions with 60-minute timeout