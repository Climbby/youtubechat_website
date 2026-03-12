# YouTube Live Chat Dashboard

A real-time dashboard for displaying YouTube Live Chat messages, optimized for readability and available as a Progressive Web App (PWA).

## Features

- **Real-time Updates**: Fetches live chat messages directly from a YouTube video.
- **Improved Readability**: Alternating background colors for chat messages.
- **PWA Ready**: Can be installed on mobile or desktop for easy access.
- **Emoji Support**: Renders YouTube chat emojis correctly.

## Prerequisites

- Python 3.7+
- A stable internet connection.

## Installation

1.  **Clone the repository** (or copy the files to your local machine).

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment**:
    - **Windows**: `venv\Scripts\activate`
    - **Mac/Linux**: `source venv/bin/activate`

4.  **Install dependencies**:
    ```bash
    pip install fastapi uvicorn pytchat jinja2
    ```

## Running the Application

1.  **Configure the Video ID**:
    Open `main.py` and change the `VIDEO_ID` variable to the ID of the YouTube Live stream you want to track.
    ```python
    VIDEO_ID = "Your_YouTube_Video_ID_Here"
    ```

2.  **Start the server**:
    ```bash
    uvicorn main:app --reload --port 8001
    ```

3.  **Access the dashboard**:
    Open your browser and navigate to `http://localhost:8001`.

## PWA Installation

You can install this dashboard as an app:
1.  Open the dashboard in Chrome or Edge.
2.  Click the "Install" icon in the address bar or find "Install App" in the browser menu.
