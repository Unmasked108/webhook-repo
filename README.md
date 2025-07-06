# GitHub Webhook Events System

A Flask-based system that receives GitHub webhook events and displays them in a real-time web interface.

## Features

- ✅ Receives GitHub webhook events (push, pull request, merge)
- ✅ Stores events in MongoDB with structured format
- ✅ Real-time UI that refreshes every 15 seconds
- ✅ Clean, responsive design
- ✅ Event type indicators and timestamps
- ✅ Error handling and connection status

## File Structure

```
webhook-repo/
├── app.py                 # Flask server
├── requirements.txt       # Python dependencies
├── config.py             # Configuration settings
├── static/
│   ├── css/
│   │   └── style.css     # UI styling
│   └── js/
│       └── app.js        # Frontend JavaScript
├── templates/
│   └── index.html        # HTML template
└── README.md             # This file
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install and start MongoDB (if not already installed)
# On macOS:
brew install mongodb/brew/mongodb-community
brew services start mongodb-community

# On Ubuntu:
sudo apt-get install mongodb
sudo systemctl start mongodb

# On Windows:
# Download and install MongoDB from https://www.mongodb.com/try/download/community
```

### 2. Configure Environment Variables (Optional)

Create a `.env` file in the root directory:

```bash
MONGODB_URI=mongodb://localhost:27017/
DATABASE_NAME=webhook_events
COLLECTION_NAME=github_events
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=True
PORT=5000
HOST=0.0.0.0
```

### 3. Run the Application

```bash
# Run the Flask development server
python app.py

# Or using gunicorn for production
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

The application will be available at `http://localhost:5000`

### 4. Set Up GitHub Webhook

1. Go to your `action-repo` on GitHub
2. Navigate to **Settings** > **Webhooks**
3. Click **Add webhook**
4. Configure the webhook:
   - **Payload URL**: `http://your-server-url:5000/webhook`
   - **Content type**: `application/json`
   - **Secret**: Leave empty or set a secret key
   - **Which events**: Select individual events:
     - ✅ Pushes
     - ✅ Pull requests
     - ✅ Pull request reviews
   - **Active**: ✅ Checked

### 5. Make Your Server Publicly Accessible

For GitHub to send webhooks to your local server, you need to make it publicly accessible:

#### Option A: Using ngrok (Recommended for development)

```bash
# Install ngrok
# Download from https://ngrok.com/download

# Expose your local server
ngrok http 5000

# Copy the https URL (e.g., https://abc123.ngrok.io)
# Use this URL in your GitHub webhook: https://abc123.ngrok.io/webhook
```

#### Option B: Deploy to a cloud service

- **Heroku**: Use the provided `requirements.txt` and `Procfile`
- **Railway**: Connect your GitHub repo and deploy
- **DigitalOcean**: Use App Platform or Droplet
- **AWS**: Use Elastic Beanstalk or EC2

## API Endpoints

- `GET /` - Main UI page
- `POST /webhook` - GitHub webhook endpoint
- `GET /api/events` - Get recent events (JSON)
- `GET /health` - Health check

## Event Format

Events are stored in MongoDB with the following structure:

```json
{
  "_id": "ObjectId",
  "timestamp": "2024-01-01T12:00:00Z",
  "event_type": "push|pull_request|merge",
  "author": "username",
  "repository": "repo-name",
  "branch": "branch-name",
  "raw_payload": {...}
}
```

## Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   - Make sure MongoDB is running: `brew services start mongodb-community`
   - Check the connection string in `config.py`

2. **Webhook Not Receiving Events**
   - Verify your webhook URL is publicly accessible
   - Check GitHub webhook delivery history for errors
   - Ensure your server is running on the correct port

3. **UI Not Updating**
   - Check browser console for JavaScript errors
   - Verify the `/api/events` endpoint is working
   - Check if the Flask server is running

### Development Tips

- Use `ngrok` for local development to expose your server
- Check GitHub webhook delivery logs for debugging
- Monitor Flask logs for incoming webhook events
- Use browser developer tools to debug frontend issues

## Testing

You can test the webhook endpoint manually:

```bash
# Test webhook endpoint
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Test events API
curl http://localhost:5000/api/events
```

## Security Considerations

- Add webhook secret verification for production
- Use HTTPS for webhook URLs
- Implement rate limiting
- Add authentication for the UI if needed
- Validate and sanitize all incoming data

## Customization

- Modify `format_event_data()` in `app.py` to handle additional event types
- Update the UI styling in `static/css/style.css`
- Add new event types or fields as needed
- Implement additional filtering or search features