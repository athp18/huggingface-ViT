import os
import sys
import json
from flask import Flask, redirect, request, session, url_for, jsonify
from flask_cors import CORS
from flask_session import Session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import google.oauth2.credentials
from exception import LoadError

# -------------------- Configuration Module --------------------

def load_json(file_path):
    """
    Load JSON configuration from a file.

    Args:
        file_path (str): The path to the JSON configuration file.

    Returns:
        dict: The configuration data parsed from the JSON file.

    Raises:
        LoadError: If the file does not exist or contains invalid JSON.
    """
    if not os.path.exists(file_path):
        raise LoadError(source=file_path, message="Config file not found")
    try:
        with open(file_path, "r") as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        raise LoadError(
            source=file_path, message="Invalid JSON format", original_error=e
        ) from e


# -------------------- Authentication Module --------------------


def get_spotify_client(config):
    """
    Get an authenticated Spotipy client using tokens stored in the session.

    Args:
        config (dict): Configuration dictionary.

    Returns:
        spotipy.Spotify: Authenticated Spotipy client.

    Raises:
        LoadError: If authentication tokens are missing or invalid.
    """
    if "spotify_token" not in session:
        raise LoadError(source="spotify_auth", message="Spotify not authenticated")

    try:
        sp_oauth = SpotifyOAuth(
            client_id=config["SPOTIPY_CLIENT_ID"],
            client_secret=config["SPOTIPY_CLIENT_SECRET"],
            redirect_uri=config["SPOTIFY_REDIRECT_URI"],
            scope=config.get("SPOTIFY_SCOPE", "playlist-read-private"),
            cache_handler=None,  # We are managing tokens manually
            show_dialog=True,
        )

        token_info = sp_oauth.validate_token(session["spotify_token"])
        if not token_info:
            raise LoadError(source="spotify_auth", message="Invalid Spotify token")

        sp = spotipy.Spotify(auth=session["spotify_token"])
        return sp
    except Exception as e:
        raise LoadError(
            source="spotify_auth",
            message="Failed to get Spotify client",
            original_error=e,
        ) from e


def get_youtube_client(config):
    """
    Get an authenticated YouTube client using tokens stored in the session.

    Args:
        config (dict): Configuration dictionary.

    Returns:
        googleapiclient.discovery.Resource: Authenticated YouTube client.

    Raises:
        LoadError: If authentication tokens are missing or invalid.
    """
    if "youtube_credentials" not in session:
        raise LoadError(source="youtube_auth", message="YouTube not authenticated")

    credentials = google.oauth2.credentials.Credentials(
        **session["youtube_credentials"]
    )

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            session["youtube_credentials"] = credentials_to_dict(credentials)
        except Exception as e:
            raise LoadError(
                source="youtube_auth",
                message="Failed to refresh YouTube credentials",
                original_error=e,
            ) from e

    try:
        youtube = build("youtube", "v3", credentials=credentials)
        return youtube
    except Exception as e:
        raise LoadError(
            source="youtube_auth",
            message="Failed to build YouTube client",
            original_error=e,
        ) from e


def credentials_to_dict(credentials):
    """
    Convert Credentials object to dict for storing in session.

    Args:
        credentials (google.oauth2.credentials.Credentials): Credentials object.

    Returns:
        dict: Dictionary representation of credentials.
    """
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }


# -------------------- Spotify Module --------------------


def get_spotify_playlist_tracks(sp, playlist_id):
    """
    Retrieve all tracks from a Spotify playlist.

    Args:
        sp (spotipy.Spotify): An authenticated Spotipy client instance.
        playlist_id (str): The Spotify Playlist ID to fetch tracks from.

    Returns:
        list: A list of track items retrieved from the Spotify playlist.

    Raises:
        LoadError: If fetching tracks fails due to a Spotipy exception.
    """
    tracks = []
    try:
        results = sp.playlist_tracks(playlist_id)
        tracks.extend(results["items"])
        while results["next"]:
            results = sp.next(results)
            tracks.extend(results["items"])
        return tracks
    except spotipy.SpotifyException as e:
        raise LoadError(
            source=f"spotify_playlist_{playlist_id}",
            message="Failed to fetch playlist tracks",
            original_error=e,
        ) from e
    except KeyError as e:
        raise LoadError(
            source=f"spotify_playlist_{playlist_id}",
            message="Invalid playlist data format",
            original_error=e,
        ) from e


# -------------------- YouTube Module --------------------


def search_youtube_instrumental(youtube, track_name, artist_name):
    """
    Search YouTube for an instrumental or karaoke version of a track.

    Args:
        youtube (googleapiclient.discovery.Resource): An authenticated YouTube client instance.
        track_name (str): The name of the track to search for.
        artist_name (str): The name of the artist of the track.

    Returns:
        str or None: The YouTube video ID of the first matching instrumental or karaoke video found.
                    Returns None if no suitable video is found.

    Raises:
        LoadError: If the YouTube API request fails.
    """
    queries = [
        f"{track_name} {artist_name} instrumental",
        f"{track_name} {artist_name} karaoke",
    ]

    for query in queries:
        try:
            request = youtube.search().list(
                part="snippet",
                maxResults=5,
                q=query,
                type="video",
                videoCategoryId="10",  # Music category
            )
            response = request.execute()
            for item in response.get("items", []):
                title = item["snippet"]["title"].lower()
                if "instrumental" in title or "karaoke" in title:
                    return item["id"]["videoId"]
        except Exception as e:
            raise LoadError(
                source="youtube_search",
                message=f"Failed to search for '{track_name}' by '{artist_name}'",
                original_error=e,
            ) from e

    return None  # No matching instrumental/karaoke version found


def create_youtube_playlist(youtube, title, description=""):
    """
    Create a new YouTube playlist.

    Args:
        youtube (googleapiclient.discovery.Resource): An authenticated YouTube client instance.
        title (str): The title of the new YouTube playlist.
        description (str, optional): The description of the new YouTube playlist. Defaults to an empty string.

    Returns:
        str: The ID of the newly created YouTube playlist.

    Raises:
        LoadError: If playlist creation fails.
    """
    try:
        request = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": description},
                "status": {"privacyStatus": "private"},
            },
        )
        response = request.execute()
        return response["id"]
    except Exception as e:
        raise LoadError(
            source="playlist creation",
            message="Failed to create the YouTube playlist",
            original_error=e,
        ) from e


def add_video_to_playlist(youtube, playlist_id, video_id):
    """
    Add a video to a YouTube playlist.

    Args:
        youtube (googleapiclient.discovery.Resource): An authenticated YouTube client instance.
        playlist_id (str): The ID of the YouTube playlist to add the video to.
        video_id (str): The YouTube video ID to be added to the playlist.

    Returns:
        None

    Raises:
        LoadError: If adding the video fails.
    """
    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        )
        request.execute()
    except Exception as e:
        raise LoadError(
            source="add video",
            message=f"Failed to add {video_id} to {playlist_id}",
            original_error=e,
        ) from e


# -------------------- Flask App Setup --------------------

app = Flask(__name__)

# Load configuration
try:
    config = load_json("config.json")
except LoadError as e:
    print(str(e))
    if e.original_error:
        print(f"Original error: {e.original_error}")
    sys.exit(1)

# Secret key for session management
app.secret_key = (
    os.getenv("FLASK_SECRET_KEY") or config.get("SECRET_KEY") or "supersecretkey"
)

# Configure server-side session
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
Session(app)

# Enable CORS
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

# -------------------- Routes --------------------


@app.route("/auth/spotify")
def auth_spotify():
    """
    Initiate Spotify OAuth flow.
    """
    sp_oauth = SpotifyOAuth(
        client_id=config["SPOTIPY_CLIENT_ID"],
        client_secret=config["SPOTIPY_CLIENT_SECRET"],
        redirect_uri=config["SPOTIFY_REDIRECT_URI"],
        scope=config.get("SPOTIFY_SCOPE", "playlist-read-private"),
        cache_handler=None,  # We are managing tokens manually
        show_dialog=True,
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route("/auth/spotify/callback")
def callback_spotify():
    """
    Handle Spotify OAuth callback.
    """
    sp_oauth = SpotifyOAuth(
        client_id=config["SPOTIPY_CLIENT_ID"],
        client_secret=config["SPOTIPY_CLIENT_SECRET"],
        redirect_uri=config["SPOTIFY_REDIRECT_URI"],
        scope=config.get("SPOTIFY_SCOPE", "playlist-read-private"),
        cache_handler=None,
        show_dialog=True,
    )

    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        return (
            jsonify({"status": "error", "message": f"Spotify OAuth error: {error}"}),
            400,
        )

    if code:
        try:
            token_info = sp_oauth.get_access_token(code, check_cache=False)
            session["spotify_token"] = token_info["access_token"]
            return jsonify(
                {"status": "success", "message": "Spotify authenticated successfully"}
            )
        except Exception as e:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Spotify authentication failed",
                        "details": str(e),
                    }
                ),
                500,
            )
    else:
        return jsonify({"status": "error", "message": "No code provided"}), 400


@app.route("/auth/youtube")
def auth_youtube():
    """
    Initiate YouTube OAuth flow.
    """
    flow = Flow.from_client_secrets_file(
        config["YOUTUBE_CLIENT_SECRETS_FILE"],
        scopes=config["YOUTUBE_SCOPES"],
        redirect_uri="http://localhost:5000/auth/youtube/callback",
    )
    auth_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true"
    )
    session["youtube_state"] = state
    return redirect(auth_url)


@app.route("/auth/youtube/callback")
def callback_youtube():
    """
    Handle YouTube OAuth callback.
    """
    state = request.args.get("state")
    if state != session.get("youtube_state"):
        return (
            jsonify({"status": "error", "message": "State mismatch in YouTube OAuth"}),
            400,
        )

    flow = Flow.from_client_secrets_file(
        config["YOUTUBE_CLIENT_SECRETS_FILE"],
        scopes=config["YOUTUBE_SCOPES"],
        state=state,
        redirect_uri="http://localhost:5000/auth/youtube/callback",
    )

    authorization_response = request.url
    try:
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "YouTube OAuth failed",
                    "details": str(e),
                }
            ),
            500,
        )

    credentials = flow.credentials
    session["youtube_credentials"] = credentials_to_dict(credentials)

    return jsonify(
        {"status": "success", "message": "YouTube authenticated successfully"}
    )


@app.route("/transfer", methods=["POST"])
def transfer_playlist():
    """
    Handle the transfer of a Spotify playlist to YouTube.

    Expected JSON Payload:
    {
        "playlist_id": "spotify_playlist_id",
        "youtube_title": "YouTube Playlist Title",
        "youtube_description": "YouTube Playlist Description"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    playlist_id = data.get("playlist_id")
    youtube_title = data.get("youtube_title")
    youtube_description = data.get("youtube_description", "")

    if not playlist_id or not youtube_title:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "playlist_id and youtube_title are required",
                }
            ),
            400,
        )

    # Check if authenticated
    if "spotify_token" not in session:
        return jsonify({"status": "error", "message": "Spotify not authenticated"}), 401
    if "youtube_credentials" not in session:
        return jsonify({"status": "error", "message": "YouTube not authenticated"}), 401

    try:
        # Authenticate with Spotify
        sp = get_spotify_client(config)

        # Fetch Spotify playlist tracks
        tracks = get_spotify_playlist_tracks(sp, playlist_id)

        # Authenticate with YouTube
        youtube = get_youtube_client(config)

        # Create YouTube playlist
        youtube_playlist_id = create_youtube_playlist(
            youtube, youtube_title, youtube_description
        )

        # Process tracks
        errors = []
        added_videos = 0
        not_found = 0

        for idx, item in enumerate(tracks, start=1):
            track = item.get("track")
            if not track:
                errors.append(f"Skipping item {idx}: No track information.")
                continue

            track_name = track.get("name")
            artists = track.get("artists", [])
            artist_names = ", ".join([artist.get("name") for artist in artists])

            try:
                video_id = search_youtube_instrumental(
                    youtube, track_name, artist_names
                )
                if video_id:
                    add_video_to_playlist(youtube, youtube_playlist_id, video_id)
                    added_videos += 1
                else:
                    not_found += 1
            except LoadError as e:
                error_msg = (
                    f"Error processing '{track_name}' by '{artist_names}': {str(e)}"
                )
                errors.append(error_msg)
                continue

        result = {
            "status": "success",
            "message": "Playlist transfer completed.",
            "details": {
                "total_tracks": len(tracks),
                "added_videos": added_videos,
                "not_found": not_found,
                "errors": errors,
            },
        }

        return jsonify(result), 200

    except LoadError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "An unexpected error occurred.",
                    "details": str(e),
                }
            ),
            500,
        )


# -------------------- Error Handlers --------------------


@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "Internal server error"}), 500


# -------------------- Run the App --------------------

if __name__ == "__main__":
    app.run(debug=True)
