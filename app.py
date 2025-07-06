from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import json
import os
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# MongoDB connection
client = MongoClient(app.config['MONGODB_URI'])
db = client[app.config['DATABASE_NAME']]
collection = db[app.config['COLLECTION_NAME']]

def format_event_data(payload):
    """Format webhook payload into standardized event data"""
    event_data = {
        'timestamp': datetime.utcnow(),
        'raw_payload': payload
    }
    
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
    
    return event_data

@app.route('/')
def index():
    """Serve the main UI page"""
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming GitHub webhook events"""
    try:
        # Get the payload
        payload = request.get_json()
        
        if not payload:
            return jsonify({'error': 'No payload received'}), 400
        
        # Format the event data
        event_data = format_event_data(payload)
        
        # Save to MongoDB
        result = collection.insert_one(event_data)
        
        print(f"Webhook received: {event_data['event_type']} by {event_data.get('author', 'Unknown')}")
        
        return jsonify({
            'status': 'success',
            'event_id': str(result.inserted_id),
            'event_type': event_data['event_type']
        }), 200
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/events')
def get_events():
    """API endpoint to fetch recent events for the UI"""
    try:
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
            else:
                formatted_event['details'] = 'performed an action'
            
            formatted_events.append(formatted_event)
        
        return jsonify(formatted_events)
        
    except Exception as e:
        print(f"Error fetching events: {str(e)}")
        return jsonify({'error': 'Failed to fetch events'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)