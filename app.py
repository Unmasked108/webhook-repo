from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import json
import os
import traceback
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# MongoDB connection with error handling
try:
    client = MongoClient(app.config['MONGODB_URI'])
    db = client[app.config['DATABASE_NAME']]
    collection = db[app.config['COLLECTION_NAME']]
    # Test the connection
    client.admin.command('ping')
    print("MongoDB connection successful")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    client = None
    db = None
    collection = None

def format_event_data(payload):
    """Format webhook payload into standardized event data"""
    event_data = {
        'timestamp': datetime.utcnow(),
        'raw_payload': payload
    }
    
    # Debug print to see what we're receiving
    print(f"Received payload keys: {list(payload.keys())}")
    print(f"Payload action: {payload.get('action')}")
    print(f"Payload zen: {payload.get('zen')}")  # GitHub ping event
    
    # Handle GitHub ping event (when webhook is first created)
    if 'zen' in payload:
        event_data.update({
            'event_type': 'ping',
            'author': 'GitHub',
            'repository': payload.get('repository', {}).get('name', 'Unknown'),
            'message': payload.get('zen', 'GitHub webhook ping')
        })
        return event_data
    
    # Handle push events
    if 'commits' in payload and payload.get('ref'):
        event_data.update({
            'event_type': 'push',
            'author': payload.get('pusher', {}).get('name', 'Unknown'),
            'branch': payload.get('ref', '').replace('refs/heads/', ''),
            'repository': payload.get('repository', {}).get('name', 'Unknown'),
            'commit_message': payload.get('head_commit', {}).get('message', '') if payload.get('head_commit') else '',
            'commit_count': len(payload.get('commits', []))
        })
    
    # Handle pull request events
    elif 'pull_request' in payload:
        pr = payload['pull_request']
        event_data.update({
            'event_type': 'pull_request',
            'author': pr.get('user', {}).get('login', 'Unknown'),
            'action': payload.get('action', 'opened'),
            'source_branch': pr.get('head', {}).get('ref', ''),
            'target_branch': pr.get('base', {}).get('ref', ''),
            'repository': payload.get('repository', {}).get('name', 'Unknown'),
            'pr_title': pr.get('title', ''),
            'pr_number': pr.get('number', '')
        })
    
    # Handle merge events (usually part of pull request closed with merged=true)
    elif payload.get('action') == 'closed' and payload.get('pull_request', {}).get('merged'):
        pr = payload['pull_request']
        event_data.update({
            'event_type': 'merge',
            'author': pr.get('merged_by', {}).get('login', 'Unknown'),
            'source_branch': pr.get('head', {}).get('ref', ''),
            'target_branch': pr.get('base', {}).get('ref', ''),
            'repository': payload.get('repository', {}).get('name', 'Unknown'),
            'pr_title': pr.get('title', ''),
            'pr_number': pr.get('number', '')
        })
    
    # Handle other events generically
    else:
        event_data.update({
            'event_type': 'unknown',
            'author': 'Unknown',
            'repository': payload.get('repository', {}).get('name', 'Unknown'),
            'action': payload.get('action', 'unknown'),
            'message': f"Received {payload.get('action', 'unknown')} event"
        })
    
    return event_data

@app.route('/')
def index():
    """Serve the main UI page"""
    try:
        return render_template('index.html')
    except Exception as e:
        # If template doesn't exist, return a simple HTML page
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Webhook Monitor</title>
        </head>
        <body>
            <h1>Webhook Monitor</h1>
            <p>Webhook endpoint is running at /webhook</p>
            <p>API endpoint is available at /api/events</p>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming GitHub webhook events"""
    try:
        # Log the incoming request
        print(f"Received webhook request: {request.method}")
        print(f"Headers: {dict(request.headers)}")
        
        # Get the payload
        payload = request.get_json()
        
        if not payload:
            print("No JSON payload received")
            return jsonify({'error': 'No payload received'}), 400
        
        print(f"Payload received: {json.dumps(payload, indent=2)}")
        
        # Format the event data
        event_data = format_event_data(payload)
        
        # Save to MongoDB if available
        if collection is not None:
            try:
                result = collection.insert_one(event_data)
                print(f"Saved to MongoDB: {result.inserted_id}")
            except Exception as mongo_error:
                print(f"MongoDB save error: {mongo_error}")
                # Continue without saving to MongoDB
        else:
            print("MongoDB not available, skipping save")
        
        print(f"Webhook processed: {event_data['event_type']} by {event_data.get('author', 'Unknown')}")
        
        return jsonify({
            'status': 'success',
            'event_type': event_data['event_type'],
            'message': 'Webhook received and processed'
        }), 200
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/events')
def get_events():
    """API endpoint to fetch recent events for the UI"""
    try:
        if collection is None:
            return jsonify({'error': 'Database not available'}), 500
            
        # Get the last 50 events, sorted by timestamp (newest first)
        events = list(collection.find().sort('timestamp', -1).limit(50))
        
        # Format events for frontend
        formatted_events = []
        for event in events:
            formatted_event = {
                'id': str(event['_id']),
                'timestamp': event['timestamp'].isoformat(),
                'event_type': event.get('event_type', 'unknown'),
                'author': event.get('author', 'Unknown'),
                'repository': event.get('repository', 'Unknown')
            }
            
            # Add event-specific details
            if event.get('event_type') == 'push':
                formatted_event['details'] = f"pushed to \"{event.get('branch', 'unknown')}\" ({event.get('commit_count', 0)} commits)"
            elif event.get('event_type') == 'pull_request':
                formatted_event['details'] = f"submitted a pull request from \"{event.get('source_branch', 'unknown')}\" to \"{event.get('target_branch', 'unknown')}\""
            elif event.get('event_type') == 'merge':
                formatted_event['details'] = f"merged branch \"{event.get('source_branch', 'unknown')}\" to \"{event.get('target_branch', 'unknown')}\""
            elif event.get('event_type') == 'ping':
                formatted_event['details'] = event.get('message', 'GitHub webhook ping')
            else:
                formatted_event['details'] = event.get('message', 'performed an action')
            
            formatted_events.append(formatted_event)
        
        return jsonify(formatted_events)
        
    except Exception as e:
        print(f"Error fetching events: {str(e)}")
        return jsonify({'error': 'Failed to fetch events'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.utcnow().isoformat(),
        'mongodb_connected': collection is not None
    })

@app.route('/debug')
def debug():
    """Debug endpoint to check configuration"""
    return jsonify({
        'mongodb_uri': app.config['MONGODB_URI'],
        'database_name': app.config['DATABASE_NAME'],
        'collection_name': app.config['COLLECTION_NAME'],
        'mongodb_connected': collection is not None
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)