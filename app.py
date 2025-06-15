import os
import re
import requests
from yt_dlp import YoutubeDL
from mutagen.mp4 import MP4, MP4Cover
from pathlib import Path
import argparse
import json
import time
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Optional imports for Spotify
try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

class MusicDownloader:
    def __init__(self, download_path=None):
        """
        Initialize the music downloader
        """
        if download_path:
            self.download_path = Path(download_path)
        else:
            self.download_path = Path.home() / "Music" / "Downloaded"
        
        self.download_path.mkdir(parents=True, exist_ok=True)
        
        # Last.fm API Key (from .env)
        self.lastfm_api_key = os.getenv('LASTFM_API_KEY')
        if not self.lastfm_api_key:
            print("⚠️ LASTFM_API_KEY not found in .env")
            print("📋 Get one at: https://www.last.fm/api/account/create")
        
        self.lastfm_base_url = "http://ws.audioscrobbler.com/2.0/"
        
        # Spotify client
        self.spotify_client = None
        self.init_spotify_client()
    
    def init_spotify_client(self):
        """
        Initialize Spotify client using credentials from .env
        """
        if not SPOTIPY_AVAILABLE:
            print("⚠️ spotipy is not installed. Install with: pip install spotipy")
            return
        
        try:
            # Get credentials from .env file
            client_id = os.getenv('SPOTIFY_CLIENT_ID')
            client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                print("⚠️ Spotify credentials not found in .env")
                print("💡 Configure in .env:")
                print("   SPOTIFY_CLIENT_ID=your_client_id")
                print("   SPOTIFY_CLIENT_SECRET=your_client_secret")
                print("📋 Get them at: https://developer.spotify.com/dashboard/")
                self.spotify_client = None
                return
            
            # Use credentials from .env
            if self._try_spotify_credentials(client_id, client_secret):
                print("✅ Spotify client initialized with .env credentials")
            else:
                print("❌ Invalid .env credentials")
                self.spotify_client = None
                
        except Exception as e:
            print(f"❌ Error initializing Spotify: {e}")
            self.spotify_client = None
    
    def _try_spotify_credentials(self, client_id, client_secret):
        """
        Test specific Spotify credentials
        """
        try:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            
            spotify_client = spotipy.Spotify(
                client_credentials_manager=client_credentials_manager
            )
            
            # Test connection
            test_result = spotify_client.search(q="test", type="track", limit=1)
            if test_result:
                self.spotify_client = spotify_client
                return True
                
        except Exception as e:
            print(f"⚠️ Error with credentials: {e}")
        
        return False
    
    def extract_spotify_playlist_with_api(self, spotify_url):
        """
        Extract playlist using official Spotify API
        """
        if not self.spotify_client:
            print("❌ Spotify client not available")
            return None
        
        try:
            # Extract playlist ID
            playlist_id = spotify_url.split('/playlist/')[1].split('?')[0]
            
            print(f"🔍 Extracting playlist with Spotify API...")
            print(f"🆔 Playlist ID: {playlist_id}")
            
            # Get playlist information
            playlist_info = self.spotify_client.playlist(playlist_id)
            playlist_name = playlist_info.get('name', 'Unknown Playlist')
            
            print(f"📋 Playlist found: {playlist_name}")
            
            tracks = []
            results = self.spotify_client.playlist_tracks(playlist_id)
            
            # Process all pages of the playlist
            while results:
                for item in results['items']:
                    track = item.get('track')
                    if track and track.get('name') and track.get('artists'):
                        track_name = track['name']
                        artists = [artist['name'] for artist in track.get('artists', [])]
                        album = track.get('album', {}).get('name', '')
                        release_date = track.get('album', {}).get('release_date', '')
                        
                        if artists:
                            query = f"{' '.join(artists)} {track_name}"
                            tracks.append({
                                'title': track_name,
                                'artist': ', '.join(artists),
                                'artists': artists,
                                'album': album,
                                'year': release_date[:4] if release_date else '',
                                'query': query,
                                'source': 'spotify_api'
                            })
                
                # Get next page if exists
                if results['next']:
                    results = self.spotify_client.next(results)
                else:
                    break
            
            print(f"✅ Extracted {len(tracks)} tracks with Spotify API")
            return tracks
            
        except Exception as e:
            print(f"❌ Error with Spotify API: {e}")
            return None
    
    def search_lastfm_track(self, query):
        """
        Search for track information on Last.fm
        """
        try:
            params = {
                'method': 'track.search',
                'track': query,
                'api_key': self.lastfm_api_key,
                'format': 'json',
                'limit': 1
            }
            
            response = requests.get(self.lastfm_base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'results' in data and 'trackmatches' in data['results']:
                    tracks = data['results']['trackmatches']['track']
                    
                    if tracks and len(tracks) > 0:
                        track = tracks[0] if isinstance(tracks, list) else tracks
                        
                        # Get additional track information
                        track_info = self.get_lastfm_track_info(track['artist'], track['name'])
                        
                        return {
                            'title': track['name'],
                            'artist': track['artist'],
                            'album': track_info.get('album', 'Unknown Album'),
                            'year': track_info.get('year', ''),
                            'artists': [track['artist']],
                            'source': 'lastfm'
                        }
            
        except Exception as e:
            print(f"⚠️ Error searching Last.fm: {e}")
        
        return None
    
    def get_lastfm_track_info(self, artist, track):
        """
        Get additional track information from Last.fm
        """
        try:
            params = {
                'method': 'track.getInfo',
                'artist': artist,
                'track': track,
                'api_key': self.lastfm_api_key,
                'format': 'json'
            }
            
            response = requests.get(self.lastfm_base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'track' in data:
                    track_data = data['track']
                    album_name = 'Unknown Album'
                    year = ''
                    
                    if 'album' in track_data and track_data['album']:
                        album_name = track_data['album'].get('title', 'Unknown Album')
                        
                        # Try to get album year
                        if 'attr' in track_data['album']:
                            year = track_data['album']['attr'].get('year', '')
                    
                    return {
                        'album': album_name,
                        'year': year
                    }
            
        except Exception as e:
            pass
        
        return {'album': 'Unknown Album', 'year': ''}
    
    def search_lastfm_album_info(self, artist, album):
        """
        Search for album information on Last.fm
        """
        try:
            params = {
                'method': 'album.getInfo',
                'artist': artist,
                'album': album,
                'api_key': self.lastfm_api_key,
                'format': 'json'
            }
            
            response = requests.get(self.lastfm_base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'album' in data:
                    album_data = data['album']
                    
                    # Search for release year
                    year = ''
                    if 'wiki' in album_data and 'published' in album_data['wiki']:
                        published = album_data['wiki']['published']
                        # Extract year from date (format: "01 Jan 2020, 00:00")
                        year_match = re.search(r'\d{4}', published)
                        if year_match:
                            year = year_match.group()
                    
                    return {'year': year}
        
        except Exception:
            pass
        
        return {'year': ''}
    
    def extract_metadata_from_youtube_title(self, title):
        """
        Extract metadata from YouTube video title
        """
        try:
            # Clean the title
            clean_title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
            clean_title = re.sub(r'\s*\[[^\]]*\]\s*$', '', clean_title)
            
            # Patterns to extract artist and title
            patterns = [
                r'^([^-]+)-\s*(.+)$',  # Artist - Title
                r'^([^•]+)•\s*(.+)$',  # Artist • Title
                r'^([^:]+):\s*(.+)$',  # Artist: Title
                r'^(.+?)\s*-\s*(.+)$', # Artist - Title (more flexible)
            ]
            
            for pattern in patterns:
                match = re.match(pattern, clean_title.strip())
                if match:
                    raw_artists = match.group(1).strip()
                    song_title = match.group(2).strip()
                    
                    # Separate multiple artists
                    artists = []
                    artist_separators = r'(?:,|\s+feat\.?\s+|\s+ft\.?\s+|\s+&\s+|\s+x\s+|\s+con\s+)'
                    artist_parts = re.split(artist_separators, raw_artists, flags=re.IGNORECASE)
                    
                    for artist in artist_parts:
                        artist = artist.strip()
                        if artist:
                            artists.append(artist)
                    
                    return {
                        'title': song_title,
                        'artist': ', '.join(artists),
                        'artists': artists,
                        'source': 'youtube'
                    }
            
            # If can't parse, return full title
            return {
                'title': clean_title,
                'artist': 'Unknown Artist',
                'artists': ['Unknown Artist'],
                'source': 'youtube_fallback'
            }
            
        except Exception as e:
            print(f"⚠️ Error extracting metadata from title: {e}")
            return None
    
    def get_best_metadata(self, spotify_metadata, lastfm_metadata, youtube_metadata, query):
        """
        Combine the best metadata from all sources
        """
        # Priority: Spotify > Last.fm > YouTube
        final_metadata = {
            'title': 'Unknown Title',
            'artist': 'Unknown Artist',
            'artists': ['Unknown Artist'],
            'album': 'Unknown Album',
            'year': '',
            'source': 'combined'
        }
        
        # If we have Spotify data (most reliable)
        if spotify_metadata:
            final_metadata.update({
                'title': spotify_metadata.get('title', final_metadata['title']),
                'artist': spotify_metadata.get('artist', final_metadata['artist']),
                'artists': spotify_metadata.get('artists', final_metadata['artists']),
                'album': spotify_metadata.get('album', final_metadata['album']),
                'year': spotify_metadata.get('year', final_metadata['year']),
                'source': 'spotify'
            })
            return final_metadata
        
        # If no Spotify, use Last.fm
        if lastfm_metadata:
            final_metadata.update({
                'title': lastfm_metadata.get('title', final_metadata['title']),
                'artist': lastfm_metadata.get('artist', final_metadata['artist']),
                'artists': lastfm_metadata.get('artists', final_metadata['artists']),
                'album': lastfm_metadata.get('album', final_metadata['album']),
                'year': lastfm_metadata.get('year', final_metadata['year']),
                'source': 'lastfm'
            })
            return final_metadata
        
        # As last resort, use YouTube
        if youtube_metadata:
            final_metadata.update({
                'title': youtube_metadata.get('title', final_metadata['title']),
                'artist': youtube_metadata.get('artist', final_metadata['artist']),
                'artists': youtube_metadata.get('artists', final_metadata['artists']),
                'source': 'youtube'
            })
            
            # Try to get album from Last.fm with YouTube data
            if final_metadata['artist'] != 'Unknown Artist':
                album_info = self.search_lastfm_album_info(
                    final_metadata['artist'], 
                    final_metadata['title']
                )
                if album_info.get('year'):
                    final_metadata['year'] = album_info['year']
        
        return final_metadata
    
    def create_playlist_file_from_spotify(self, spotify_url, filename=None):
        """
        Create playlist file automatically from Spotify
        """
        print("🎵 Extracting tracks from Spotify...")
        
        # Try with Spotify API first
        tracks = self.extract_spotify_playlist_with_api(spotify_url)
        
        if not tracks:
            print("❌ Could not extract with Spotify API")
            return self.create_manual_playlist_template(spotify_url, filename)
        
        # Generate filename
        if not filename:
            timestamp = int(time.time())
            filename = f"spotify_playlist_{timestamp}.txt"
        elif not filename.endswith('.txt'):
            filename = f"{filename}.txt"
        
        # Create the file
        file_path = Path(filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# Playlist automatically extracted from Spotify\n")
                f.write(f"# URL: {spotify_url}\n")
                f.write(f"# Total tracks: {len(tracks)}\n")
                f.write(f"# Method: Official Spotify API\n")
                f.write(f"# Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for track in tracks:
                    f.write(f"{track['query']}\n")
            
            print(f"✅ File created: {file_path}")
            print(f"📋 Tracks extracted: {len(tracks)}")
            
            # Preview
            print("\n🎵 Preview:")
            for i, track in enumerate(tracks[:5], 1):
                print(f"   {i}. {track['query']}")
            
            if len(tracks) > 5:
                print(f"   ... and {len(tracks) - 5} more")
            
            return file_path
            
        except Exception as e:
            print(f"❌ Error creating file: {e}")
            return None
    
    def create_manual_playlist_template(self, spotify_url, custom_name=None):
        """
        Create a manual template as fallback
        """
        try:
            playlist_id = spotify_url.split('/playlist/')[1].split('?')[0]
        except:
            playlist_id = "manual"
        
        if custom_name:
            template_file = f"{self.sanitize_filename(custom_name)}.txt"
        else:
            template_file = f"spotify_playlist_{playlist_id}.txt"
        
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write("# Manual Playlist - Spotify\n")
            f.write(f"# Original URL: {spotify_url}\n")
            f.write("# Spotify API did not work\n")
            f.write("# Instructions:\n")
            f.write("# 1. Open your playlist in Spotify\n")
            f.write("# 2. Copy each song in format: Artist Song\n")
            f.write("# 3. One song per line\n")
            f.write("# 4. Remove these comment lines\n\n")
            f.write("# Examples:\n")
            f.write("# Bad Bunny Dakiti\n")
            f.write("# Quevedo Bzrp Music Sessions 52\n\n")
            f.write("# Add your tracks here:\n")
        
        print(f"📄 Manual template created: {template_file}")
        return template_file
    
    def sanitize_filename(self, filename):
        """Clean filename"""
        return re.sub(r'[<>:"/\\|?*]', '', filename)
    
    def create_filename_from_metadata(self, metadata):
        """Create filename from metadata"""
        if not metadata:
            return None
        
        title = metadata.get('title', '')
        artists = metadata.get('artists', [])
        
        if not title:
            return None
        
        if not artists and metadata.get('artist'):
            artists = [metadata.get('artist')]
        
        if not artists:
            return self.sanitize_filename(title)
        
        # Format: "title - artist1 - artist2"
        filename_parts = [title] + artists
        filename = ' - '.join(filename_parts)
        
        return self.sanitize_filename(filename)
    
    def download_thumbnail(self, thumbnail_url, file_path):
        """Download video thumbnail"""
        try:
            response = requests.get(thumbnail_url, timeout=10)
            if response.status_code == 200:
                thumbnail_path = file_path.parent / f"{file_path.stem}_thumb.jpg"
                with open(thumbnail_path, 'wb') as f:
                    f.write(response.content)
                return thumbnail_path
        except Exception as e:
            print(f"⚠️ Error downloading thumbnail: {e}")
        return None
    
    def load_tracks_from_file(self, file_path):
        """Load tracks from text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            tracks = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    tracks.append({
                        'title': line,
                        'query': line,
                        'artist': '',
                    })
            
            return tracks
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return []
    
    def extract_youtube_playlist_data(self, youtube_url):
        """Extract YouTube playlist"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(youtube_url, download=False)
                
                if 'entries' in playlist_info:
                    tracks = []
                    for entry in playlist_info['entries']:
                        if entry and 'title' in entry:
                            tracks.append({
                                'title': entry['title'],
                                'query': entry['title'],
                                'url': entry.get('url', ''),
                                'id': entry.get('id', '')
                            })
                    
                    return tracks
            
        except Exception as e:
            print(f"❌ Error extracting YouTube playlist: {e}")
        
        return []
    
    def detect_input_type(self, input_str):
        """Detect input type"""
        if input_str.endswith('.txt') and os.path.exists(input_str):
            return 'file'
        
        if 'youtube.com' in input_str and ('playlist' in input_str or 'list=' in input_str):
            return 'youtube'
        elif 'youtu.be' in input_str:
            return 'youtube'
        
        if 'spotify.com' in input_str and 'playlist' in input_str:
            return 'spotify'
        
        return 'search'
    
    def download_playlist_from_source(self, source, custom_folder=None, extract_only=False):
        """Download playlist from different sources"""
        input_type = self.detect_input_type(source)
        
        print(f"🎵 Detected: {input_type.upper()}")
        
        if input_type == 'spotify':
            print(f"🔍 Extracting Spotify playlist...")
            
            filename = f"{self.sanitize_filename(custom_folder)}.txt" if custom_folder else None
            playlist_file = self.create_playlist_file_from_spotify(source, filename)
            
            if not playlist_file:
                return []
            
            if extract_only:
                print(f"\n📄 List extracted to: {playlist_file}")
                print("💡 To download tracks run:")
                print(f"   python app.py \"{playlist_file}\" --playlist-name \"{custom_folder or 'My Playlist'}\"")
                return []
            
            source = str(playlist_file)
            input_type = 'file'
        
        print(f"🔍 Extracting information...")
        
        if input_type == 'file':
            tracks = self.load_tracks_from_file(source)
            print(f"📄 Loading from file: {source}")
        elif input_type == 'youtube':
            tracks = self.extract_youtube_playlist_data(source)
            print(f"📺 Extracting YouTube playlist")
        else:
            print("❌ Unrecognized input type")
            return []
        
        if not tracks:
            print("❌ Could not extract tracks")
            return []
        
        print(f"📋 Found {len(tracks)} tracks")
        
        # Create destination folder
        if custom_folder:
            playlist_folder = self.download_path / self.sanitize_filename(custom_folder)
        else:
            playlist_name = Path(source).stem if input_type == 'file' else f"Playlist_{int(time.time())}"
            playlist_folder = self.download_path / playlist_name
        
        playlist_folder.mkdir(parents=True, exist_ok=True)
        
        # Change path temporarily
        original_path = self.download_path
        self.download_path = playlist_folder
        
        downloaded_files = []
        failed_downloads = []
        
        # Download each track
        for i, track in enumerate(tracks, 1):
            print(f"\n📥 Downloading {i}/{len(tracks)}: {track['query']}")
            
            try:
                result = self.download_track(track['query'])
                if result:
                    downloaded_files.append(result)
                    print(f"✅ Completed")
                else:
                    failed_downloads.append(track['query'])
                    print(f"❌ Failed")
                
                time.sleep(1)  # Avoid rate limiting
                
            except Exception as e:
                print(f"❌ Error: {e}")
                failed_downloads.append(track['query'])
        
        # Restore path
        self.download_path = original_path
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"✅ Completed: {len(downloaded_files)}")
        print(f"❌ Failed: {len(failed_downloads)}")
        print(f"📁 Saved to: {playlist_folder}")
        
        if failed_downloads:
            print(f"\n⚠️ Failed tracks:")
            for failed in failed_downloads[:5]:  # Only show first 5
                print(f"   - {failed}")
            if len(failed_downloads) > 5:
                print(f"   ... and {len(failed_downloads) - 5} more")
        
        return downloaded_files
    
    def download_track(self, query, custom_filename=None):
        """Download an individual track"""
        try:
            # 1. Search Last.fm first for metadata
            print(f"🔍 Searching metadata on Last.fm...")
            lastfm_metadata = self.search_lastfm_track(query)
            
            # 2. Search on YouTube
            print(f"🔍 Searching on YouTube...")
            ydl_opts_info = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with YoutubeDL(ydl_opts_info) as ydl:
                search_query = f"ytsearch1:{query}"
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info and info['entries']:
                    video_info = info['entries'][0]
                    print(f"🎵 Found: {video_info['title']}")
                    
                    # 3. Extract metadata from YouTube title
                    youtube_metadata = self.extract_metadata_from_youtube_title(video_info['title'])
                    
                    # 4. Combine best metadata
                    final_metadata = self.get_best_metadata(None, lastfm_metadata, youtube_metadata, query)
                    final_metadata['thumbnail'] = video_info.get('thumbnail', '')
                    
                    print(f"📋 Metadata: {final_metadata['artist']} - {final_metadata['title']}")
                    print(f"💿 Album: {final_metadata['album']} ({final_metadata['year']})")
                    
                    # 5. Create filename
                    if custom_filename:
                        filename = self.sanitize_filename(custom_filename)
                    else:
                        filename = self.create_filename_from_metadata(final_metadata)
                        if not filename:
                            filename = self.sanitize_filename(video_info['title'])
                    
                    # 6. Download audio
                    print(f"⬇️ Downloading audio...")
                    ydl_opts_download = {
                        'format': '140/bestaudio[ext=m4a]/bestaudio[acodec*=aac]/bestaudio',
                        'outtmpl': str(self.download_path / f'{filename}.%(ext)s'),
                        'writeinfojson': False,
                        'writethumbnail': False,
                        'quiet': True,
                        'no_warnings': True,
                    }
                    
                    with YoutubeDL(ydl_opts_download) as ydl_download:
                        ydl_download.download([video_info['webpage_url']])
                    
                    # 7. Find downloaded file
                    downloaded_file = None
                    for ext in ['m4a', 'aac', 'mp4', 'webm']:
                        pattern = f"{filename}.{ext}"
                        matches = list(self.download_path.glob(pattern))
                        if matches:
                            downloaded_file = matches[0]
                            break
                    
                    if not downloaded_file:
                        # Search for recent audio files
                        audio_extensions = ['*.m4a', '*.aac', '*.mp4', '*.webm']
                        audio_files = []
                        for ext in audio_extensions:
                            audio_files.extend(self.download_path.glob(ext))
                        
                        if audio_files:
                            downloaded_file = max(audio_files, key=lambda f: f.stat().st_mtime)
                    
                    # 8. Add metadata and thumbnail
                    if downloaded_file:
                        print(f"🏷️ Adding metadata...")
                        
                        # Download thumbnail
                        thumbnail_path = None
                        if final_metadata.get('thumbnail'):
                            thumbnail_path = self.download_thumbnail(final_metadata['thumbnail'], downloaded_file)
                        
                        # Add metadata to file
                        if downloaded_file.suffix.lower() in ['.m4a', '.mp4']:
                            self.add_metadata(downloaded_file, final_metadata, thumbnail_path)
                        
                        # Clean temporary thumbnail
                        if thumbnail_path and thumbnail_path.exists():
                            thumbnail_path.unlink()
                        
                        print(f"✅ Download completed")
                        return str(downloaded_file)
                
                return None
                
        except Exception as e:
            print(f"❌ Error downloading: {e}")
            return None
    
    def add_metadata(self, file_path, metadata, thumbnail_path=None):
        """Add metadata to audio file"""
        try:
            audio_file = MP4(file_path)
            
            # Basic metadata
            audio_file['\xa9nam'] = metadata.get('title', '')  # Title
            audio_file['\xa9ART'] = metadata.get('artist', '')  # Artist
            audio_file['\xa9alb'] = metadata.get('album', 'Single')  # Album
            audio_file['\xa9day'] = metadata.get('year', '')  # Year
            audio_file['\xa9gen'] = 'Music'  # Genre
            
            # Multiple artists
            if metadata.get('artists') and len(metadata['artists']) > 1:
                audio_file['\xa9ART'] = metadata['artists'][0]  # Main artist
                audio_file['aART'] = ', '.join(metadata['artists'])  # All artists
            
            # Add cover art
            if thumbnail_path and thumbnail_path.exists():
                with open(thumbnail_path, 'rb') as f:
                    thumbnail_data = f.read()
                    audio_file['covr'] = [MP4Cover(thumbnail_data, MP4Cover.FORMAT_JPEG)]
            
            audio_file.save()
            
        except Exception as e:
            print(f"⚠️ Error adding metadata: {e}")

def main():
    parser = argparse.ArgumentParser(description='Music downloader with Spotify and Last.fm')
    parser.add_argument('query', help='Song, .txt file, Spotify/YouTube playlist URL')
    parser.add_argument('--filename', '-f', help='Custom filename')
    parser.add_argument('--path', '-p', help='Download path')
    parser.add_argument('--playlist-name', '-n', help='Folder name for playlist')
    parser.add_argument('--extract-only', '-e', action='store_true', help='Only extract Spotify list to file')
    
    args = parser.parse_args()
    
    downloader = MusicDownloader(download_path=args.path)
    
    print(f"📁 Download path: {downloader.download_path}")
    
    input_type = downloader.detect_input_type(args.query)
    
    if input_type in ['file', 'youtube', 'spotify']:
        # It's a playlist
        results = downloader.download_playlist_from_source(
            args.query, 
            args.playlist_name, 
            extract_only=args.extract_only
        )
        
        if results:
            print(f"\n🎉 Download completed with {len(results)} tracks")
        elif not args.extract_only:
            print("\n💥 Could not download playlist")
    else:
        # It's an individual song
        if args.extract_only:
            print("⚠️ --extract-only only works with playlists")
            return
            
        result = downloader.download_track(args.query, args.filename)
        if result:
            print(f"\n🎵 File saved to: {result}")
        else:
            print("\n💥 Could not download track")

if __name__ == "__main__":
    main()