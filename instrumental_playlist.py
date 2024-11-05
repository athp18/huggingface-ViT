import os
import sys
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# -------------------- Configuration Module --------------------

def load_config(file_path):
    """
    Load JSON configuration from a file.

    Args:
        file_path (str): The path to the JSON configuration file.

    Returns:
        dict: The configuration data parsed from the JSON file.

    Exits:
        If the file does not exist or contains invalid JSON, the program exits with an error message.
    """
    if not os.path.exists(file_path):
        print(f"Configuration file {file_path} not found.")
        sys.exit(1)
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        print(f"Error parsing {file_path}: {e}")
        sys.exit(1)

# -------------------- Authentication Module --------------------

def authenticate_spotify(config):
    """
    Authenticate with Spotify using Spotipy and return the Spotify client.

    Args:
        config (dict): A dictionary containing Spotify authentication credentials and settings.
            Expected keys:
                - "SPOTIPY_CLIENT_ID" (str): Spotify API client ID.
                - "SPOTIPY_CLIENT_SECRET" (str): Spotify API client secret.
                - "SPOTIFY_REDIRECT_URI" (str): Redirect URI for Spotify OAuth.
                - "SPOTIFY_SCOPE" (str, optional): Spotify OAuth scopes. Defaults to "playlist-read-private".

    Returns:
        spotipy.Spotify: An authenticated Spotipy client instance.

    Exits:
        If authentication fails, the program exits with an error message.
    """
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=config["SPOTIPY_CLIENT_ID"],
            client_secret=config["SPOTIPY_CLIENT_SECRET"],
            redirect_uri=config["SPOTIFY_REDIRECT_URI"],
            scope=config.get("SPOTIFY_SCOPE", "playlist-read-private")
        ))
        return sp
    except Exception as e:
        print(f"Spotify authentication failed: {e}")
        sys.exit(1)

def authenticate_youtube(client_secrets_file, scopes):
    """
    Authenticate with YouTube using OAuth 2.0 and return the YouTube client.

    Args:
        client_secrets_file (str): Path to the YouTube API client secrets JSON file.
        scopes (list of str): A list of OAuth 2.0 scopes required for YouTube API access.

    Returns:
        googleapiclient.discovery.Resource: An authenticated YouTube client instance.

    Exits:
        If the client secrets file is not found or authentication fails, the program exits with an error message.
    """
    if not os.path.exists(client_secrets_file):
        print(f"ERROR: {client_secrets_file} file not found.")
        sys.exit(1)
    try:
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        credentials = flow.run_local_server(port=0)
        youtube = build("youtube", "v3", credentials=credentials)
        return youtube
    except Exception as e:
        print(f"YouTube authentication failed: {e}")
        sys.exit(1)

# -------------------- Spotify Module --------------------

def get_spotify_playlist_tracks(sp, playlist_id):
    """
    Retrieve all tracks from a Spotify playlist.

    Args:
        sp (spotipy.Spotify): An authenticated Spotipy client instance.
        playlist_id (str): The Spotify Playlist ID to fetch tracks from.

    Returns:
        list: A list of track items retrieved from the Spotify playlist.

    Exits:
        If fetching tracks fails due to a Spotipy exception, the program exits with an error message.
    """
    tracks = []
    try:
        results = sp.playlist_tracks(playlist_id)
        tracks.extend(results['items'])
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        return tracks
    except spotipy.SpotifyException as e:
        print(f"Error fetching Spotify playlist tracks: {e}")
        sys.exit(1)

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

    Notes:
        The search prioritizes videos with "instrumental" or "karaoke" in the title within the Music category.
    """
    queries = [
        f"{track_name} {artist_name} instrumental",
        f"{track_name} {artist_name} karaoke"
    ]
    
    for query in queries:
        try:
            request = youtube.search().list(
                part="snippet",
                maxResults=5,
                q=query,
                type="video",
                videoCategoryId="10"  # Music category
            )
            response = request.execute()
            for item in response.get('items', []):
                title = item['snippet']['title'].lower()
                if 'instrumental' in title or 'karaoke' in title:
                    return item['id']['videoId']
        except Exception as e:
            print(f"Error searching YouTube for '{track_name}' by '{artist_name}': {e}")
    
    return None
def create_youtube_playlist(youtube, title, description=""):
    """
    Create a new YouTube playlist.

    Args:
        youtube (googleapiclient.discovery.Resource): An authenticated YouTube client instance.
        title (str): The title of the new YouTube playlist.
        description (str, optional): The description of the new YouTube playlist. Defaults to an empty string.

    Returns:
        str: The ID of the newly created YouTube playlist.

    Exits:
        If playlist creation fails, the program exits with an error message.
    """
    try:
        request = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description
                },
                "status": {
                    "privacyStatus": "private"
                }
            }
        )
        response = request.execute()
        return response['id']
    except Exception as e:
        print(f"Error creating YouTube playlist: {e}")
        sys.exit(1)

def add_video_to_playlist(youtube, playlist_id, video_id):
    """
    Add a video to a YouTube playlist.

    Args:
        youtube (googleapiclient.discovery.Resource): An authenticated YouTube client instance.
        playlist_id (str): The ID of the YouTube playlist to add the video to.
        video_id (str): The YouTube video ID to be added to the playlist.

    Returns:
        None

    Notes:
        If adding the video fails, an error message is printed but the program continues.
    """
    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        )
        request.execute()
    except Exception as e:
        print(f"Error adding video ID {video_id} to playlist: {e}")

# -------------------- Main Module --------------------

def main():
    """
    The main function orchestrates the process of transferring a Spotify playlist to YouTube.

    Steps:
        1. Load configuration from 'config.json'.
        2. Authenticate with Spotify using the loaded configuration.
        3. Retrieve the Spotify playlist ID from the configuration or user input.
        4. Fetch all tracks from the specified Spotify playlist.
        5. Authenticate with YouTube using 'client_secrets.json'.
        6. Create a new YouTube playlist with user-provided title and description.
        7. For each track in the Spotify playlist:
            a. Search for an instrumental or karaoke version on YouTube.
            b. If found, add the video to the YouTube playlist.
            c. If not found, log that the instrumental was not found.
        8. Notify the user upon completion.

    Returns:
        None
    """
    # Load configuration
    config = load_config('./config.json')
    print("Authenticating with Spotify...")
    sp = authenticate_spotify(config)

    playlist_id = config.get("PLAYLIST_ID")
    if not playlist_id:
        playlist_id = input("Enter Spotify Playlist ID: ").strip()
        if not playlist_id:
            print("Playlist ID is required. Defaulting to my playlist...")
            playlist_id = "0mf8qkcdAMJ6UcJC7crcys"

    print("Fetching tracks from Spotify playlist...")
    tracks = get_spotify_playlist_tracks(sp, playlist_id)
    print(f"Found {len(tracks)} tracks.")

    print("Authenticating with YouTube...")
    youtube = authenticate_youtube("client_secrets.json", ["https://www.googleapis.com/auth/youtube"])

    playlist_title = input("Enter title for the new YouTube playlist: ").strip()
    playlist_description = input("Enter description for the new YouTube playlist (optional): ").strip()
    youtube_playlist_id = create_youtube_playlist(youtube, playlist_title, playlist_description)
    print(f"Created YouTube playlist with ID: {youtube_playlist_id}")

    for idx, item in enumerate(tracks, start=1):
        track = item.get('track')
        if not track:
            print(f"({idx}/{len(tracks)}) Skipping item with no track information.")
            continue
        track_name = track.get('name')
        artists = track.get('artists', [])
        artist_names = ', '.join([artist.get('name') for artist in artists])
        print(f"({idx}/{len(tracks)}) Searching instrumental for: '{track_name}' by '{artist_names}'")
        video_id = search_youtube_instrumental(youtube, track_name, artist_names)
        if video_id:
            add_video_to_playlist(youtube, youtube_playlist_id, video_id)
            print(f"Added video ID {video_id} to YouTube playlist.")
        else:
            print(f"Instrumental not found for: '{track_name}' by '{artist_names}'")

    print("YouTube playlist creation complete!")

if __name__ == "__main__":
    main()