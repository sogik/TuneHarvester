# 🎵 TuneHarvester

Music tool with Spotify/Youtube playlist extraction and more.

## Features

- 🎵 **Multiple Sources**: Spotify playlists, YouTube playlists, individual tracks
- 📋 **Smart Metadata**: Combines Spotify API + Last.fm for complete track information
- 🎯 **High Quality Audio**: Downloads best available audio format (M4A/AAC)
- 📁 **Organized Downloads**: Automatic folder structure and filename formatting
- ⚡ **Fast & Efficient**: No browser automation, pure API integration
- 🔒 **Privacy Focused**: No telemetry, diagnostics or user data collection
- 📖 **Open Source**: Free and libre software under BSD-3-Clause license

> [!NOTE]
> It is still **recommended** to support creators by engaging with their YouTube channels/Spotify tracks (or preferably by buying their merch/concert tickets/physical media).

## Installation

1. **Clone repository**:

```bash
git clone https://github.com/sogik/TuneHarvester.git
cd TuneHarvester
```

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Configure environment variables**:

```bash
cp .env.example .env
# Edit .env with your credentials
```

## Get Credentials

### Spotify API (Required for Spotify playlists)

1. Go to: https://developer.spotify.com/dashboard/
2. Create a new application
3. Copy **Client ID** and **Client Secret** to `.env`

### Last.fm API (Optional - for enhanced metadata)

1. Go to: https://www.last.fm/api/account/create
2. Create a developer account
3. Copy your **API Key** to `.env`

## Usage

### Spotify Playlist

```bash
python app.py "https://open.spotify.com/...." --playlist-name "Today's Top Hits"
```

### YouTube Playlist

```bash
python app.py "https://www.youtube.com/playlist?list=...." --playlist-name "My Mix"
```

### Individual Song

```bash
python app.py "Artist Song"
```

### Text File Playlist

```bash
python app.py my_songs.txt --playlist-name "Custom Mix"
```

### Extract Only (No Download)

```bash
python app.py "https://open.spotify.com/playlist/..." --extract-only
```

### Custom Download Path

```bash
python app.py "Artist Song" --path "/path/to/downloads"
```

## Legal Notice

> [!CAUTION]
> This software is provided for educational and personal use only. Users are responsible for complying with applicable copyright laws and terms of service. Please support artists by purchasing their music.
> This software is provided for educational and personal use only. Users are responsible for complying with applicable copyright laws and terms of service. Please support artists by purchasing their music.

## License

TuneHarvester is open source and licensed under the [BSD-3-Clause](/LICENSE) License.
