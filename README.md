## Convert your Spotify playlists to their instrumental versions!

To run this script, do the following:

1. Step 1: Clone the repository.
```
git clone https://github.com/athp18/spotify_to_yt_instrumentals.git
cd spotify_to_yt_instrumentals
```
2. Download the required libraries with:
```
pip install -r requirements.txt
```
3. Set up Spotify API credentials by going to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard). Create a **Client ID** and **Client Secret**. Set the **Redirect URI** in your Spotify application settings (e.g., `http://localhost:8888/callback`). Edit the `config.json` file and add that info.
4. Set Up YouTube Data API Credentials. Go to the [Google Developer Console](https://cloud.google.com/cloud-console?utm_source=google&utm_medium=cpc&utm_campaign=na-US-all-en-dr-bkws-all-all-trial-b-dr-1707554&utm_content=text-ad-none-any-DEV_c-CRE_665735422256-ADGP_Hybrid+%7C+BKWS+-+MIX+%7C+Txt-Management+Tools-Cloud+Console-KWID_43700077225654723-aud-1909161378652:kwd-296393718382&utm_term=KW_google%20cloud%20console-ST_google+cloud+console&gad_source=1&gclid=Cj0KCQiA_qG5BhDTARIsAA0UHSItEnjXBrSql4wCP6_Oybj5P9SUzdmPbqyhskhdv50ZushwmItnTvcaAk2LEALw_wcB&gclsrc=aw.ds). Create a new project. Enable the YouTube Data API v3 for your project. Create OAuth 2.0 credentials and download the client_secrets.json file to the project directory.
5. Edit the `config.json` file to contain the ID of the playlist you want to convert to instrumentals.
6. Run the script with:
```
python cli.py
```
