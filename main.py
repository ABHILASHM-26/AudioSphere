from dotenv import load_dotenv
import os
import base64
from requests import post, get
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")


app = Flask(__name__)
app.secret_key = 'b2bae02d5207b0ba9995e118f61ac8e6'


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, 'instance')
DB_NAME = os.path.join(DB_DIR, 'users.db')
os.makedirs(DB_DIR, exist_ok=True)


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        conn.commit()


init_db()


def getToken():
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    response = post(url, headers=headers, data=data)

    if response.status_code != 200:
        print(f"Error fetching token: {response.status_code} - {response.text}")
        return None

    return response.json().get("access_token")


def getAuthHeader(token):
    return {"Authorization": "Bearer " + token}

def searchArtist(token, artistName):
    url = "https://api.spotify.com/v1/search"
    headers = getAuthHeader(token)
    query = f"?q={artistName}&type=artist&limit=1"

    queryurl = url + query
    result = get(queryurl, headers=headers)
    json_result = json.loads(result.content)["artists"]["items"]
    if len(json_result) == 0:
        print("No artist found")
        return None

    return json_result[0]

def getAlbums(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=album,single&limit=50"
    headers = getAuthHeader(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)["items"]
    return json_result

def getTracks(token, album_id):
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    headers = getAuthHeader(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)["items"]
    return json_result

def getSongs(token, artist_id):
    albums = getAlbums(token, artist_id)
    songs_with_photo = []
    for album in albums:
        tracks = getTracks(token, album["id"])
        for i, track in enumerate(tracks):
            if len(songs_with_photo) >= 40:  
                break
            if i > 0:  
                break
            song_details = {
                "id": track["id"],
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "photo_url": getPhoto(token, track["id"]),
                "song_url": getSpotifyLink(track["id"])  
            }
            songs_with_photo.append(song_details)
        if len(songs_with_photo) >= 80:  
            break
    return songs_with_photo

def getPhoto(token, track_id):
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    headers = getAuthHeader(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)
    if "album" in json_result and "images" in json_result["album"]:
        images = json_result["album"]["images"]
        if images:
            return images[0]["url"]
    return None

def getSongUrl(token, track_id):
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    headers = getAuthHeader(token)
    response = get(url, headers=headers)
    json_result = response.json()
    return json_result.get("preview_url")


def getSpotifyLink(track_id):
    return f"https://open.spotify.com/track/{track_id}"


def search_artist_id(token, artist_name):
    url = "https://api.spotify.com/v1/search"
    headers = getAuthHeader(token)
    params = {
        "q": artist_name,
        "type": "artist",
        "limit": 1
    }
    response = get(url, headers=headers, params=params)
    data = response.json()
    artists = data.get('artists', {}).get('items', [])
    if not artists:
        return None
    return artists[0]['id']

def getTrendingSongsByArtist(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country=IN"
    headers = getAuthHeader(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)["tracks"]
    
    trending_songs = []
    for track in json_result:
        song_details = {
            "id": track["id"],
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "photo_url": getPhoto(token, track["id"]),  
            "song_url": getSongs(token,track["id"])    
        }
        trending_songs.append(song_details)
        
    return trending_songs

def getFeaturedPlaylists(token, country="IN"):
    url = f"https://api.spotify.com/v1/browse/featured-playlists?country={country}&limit=10"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["playlists"]["items"]
    return []

def getPlaylistTracks(token, playlist_id):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = getAuthHeader(token)
    response = get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error fetching playlist tracks: {response.status_code} - {response.text}")
        return []

    data = response.json().get("items", [])
    return [item["track"] for item in data if item.get("track")]


def getTrendingSongs(token):
    url = 'https://api.spotify.com/v1/browse/new-releases?limit=48'
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(url, headers=headers)
    
    songs = []
    if response.status_code == 200:
        data = response.json()
        for item in data['albums']['items']:
            song = {
                'name': item['name'],
                'artist': item['artists'][0]['name'],
                'song_url': item['external_urls']['spotify'], 
                'photo_url': item['images'][0]['url']
            }
            songs.append(song)
    return songs


def getSongsByGenre(token, genre):
    url = "https://api.spotify.com/v1/recommendations"
    headers = getAuthHeader(token)
    params = {
        "seed_genres": genre,
        "limit": 80
    }
    response = get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Error fetching songs for genre {genre}: {response.status_code} - {response.text}")
        return []

    data = response.json()
    tracks = data.get('tracks', [])
    
    songs = []
    for track in tracks:
        if not track.get("preview_url"):
            continue 

        song_details = {
            "id": track["id"],
            "name": track["name"],
            "artist": ", ".join(artist["name"] for artist in track["artists"]),
            "photo_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "song_url": track["preview_url"]
        }
        songs.append(song_details)

    return songs

app = Flask(__name__,static_url_path='/static')

@app.route('/')
def index():
    token = getToken()
    if not token:
        return "Error fetching token", 500

    songs = getTrendingSongs(token)
    return render_template('home.html', songs=songs, username=session.get('username'), email=session.get('email'))


@app.route('/search', methods=['POST'])
def search():
    artist_name = request.form['artist']
    token = getToken()
    result = searchArtist(token,artist_name)
    if result:
        artist_id = result["id"]
        songs = getSongs(token, artist_id)
        for song in songs:
            song['photo_url'] = getPhoto(token, song['id'])
            song['song_url'] = getSongUrl(token,song['id'])
    else:
        songs = None  
    return render_template('songs.html', songs=songs)

@app.route('/artist/<artist_id>')
def artist(artist_id):
    token = getToken()
    songs = getTrendingSongs(token, artist_id)
    for song in songs:
        song['photo_url'] = getPhoto(token, song['id'])
        song['song_url'] = getSpotifyLink(song['id'])
    return render_template('home.html', songs=songs)

@app.route('/artist/<artist_name>')
def artist_songs(artist_name):
    token = getToken()
    artist_id = search_artist_id(token, artist_name)
    if not artist_id:
        return "Artist not found", 404

    songs = getSongs(token, artist_id)
    for song in songs:
        song['photo_url'] = getPhoto(token, song['id'])
        song['song_url'] = getSpotifyLink(song['id'])
    return render_template('song.html', songs=songs)


@app.route('/artist.html')
def artists():
    return render_template('artist.html')


@app.route('/genres.html')
def genres():
    return render_template('genres.html')

@app.route('/artist.html/<artist_name>')
def song(artist_name):
    token = getToken()
    result = searchArtist(token, artist_name)
    if result:
        artist_id = result["id"]
        songs = getSongs(token, artist_id)
        for song in songs:
            song['photo_url'] = getPhoto(token, song['id'])
            song['song_url'] = getSongUrl(token,song['id'])
    else:
        songs = None  
    

    return render_template('songs.html', songs=songs)


@app.route('/search_songs', methods=['POST'])
def search_songs():
    query = request.form['query']
    token = getToken()
    if not token:
        return "Error fetching token", 500
    
   
    url = "https://api.spotify.com/v1/search"
    headers = getAuthHeader(token)
    params = {
        "q": query,
        "type": "track",
        "limit": 30 
    }
    response = get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        return f"Error searching for songs: {response.status_code} - {response.text}", 500
    
    data = response.json()
    tracks = data.get('tracks', {}).get('items', [])
    
    songs = []
    for track in tracks:
        song_details = {
            "id": track["id"],
            "name": track["name"],
            "artist": ", ".join(artist["name"] for artist in track["artists"]),
            "photo_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
           
            "song_url": getSongUrl(token,track['id'])
        }
        songs.append(song_details)
    
    return render_template('songs.html', songs=songs)


@app.route('/genres/<genre_name>')
def genre_songs(genre_name):
    token = getToken()
    if not token:
        return "Error fetching token", 500

    songs = getSongsByGenre(token, genre_name)
    if not songs:
        return "No songs found for this genre", 404
    
    return render_template('songGenre.html', genre=genre_name, songs=songs)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                username = data.get('username', '').strip()
                email = data.get('email', '').strip()
                password = data.get('password', '').strip()
            else:
                username = request.form.get('username', '').strip()
                email = request.form.get('email', '').strip()
                password = request.form.get('password', '').strip()

            if not username or not email or not password:
                message = "All fields are required"
                if request.is_json:
                    return jsonify({"error": message}), 400
                return render_template('signup.html', error=message)

            hashed_password = generate_password_hash(password)

            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                          (username, email, hashed_password))
                conn.commit()

            if request.is_json:
                return jsonify({"message": "Signup successful"}), 201

            return redirect(url_for('profile', username=username, email=email))

        except sqlite3.IntegrityError:
            message = "Email already registered"
            if request.is_json:
                return jsonify({"error": message}), 409
            return render_template('signup.html', error=message)

        except Exception as e:
            message = str(e)
            if request.is_json:
                return jsonify({"error": message}), 500
            return render_template('signup.html', error=message)

    return render_template('signup.html')


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                email = data.get('email', '').strip()
                password = data.get('password', '').strip()
            else:
                email = request.form.get('email', '').strip()
                password = request.form.get('password', '').strip()

            if not email or not password:
                message = "Email and password are required"
                if request.is_json:
                    return jsonify({"error": message}), 400
                return render_template('signin.html', error=message)

            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("SELECT username, password FROM users WHERE email = ?", (email,))
                result = c.fetchone()

            if result and check_password_hash(result[1], password):
                username = result[0]
                if request.is_json:
                    return jsonify({
                        "message": "Signin successful",
                        "username": username,
                        "email": email
                    }), 200
                return redirect(url_for('profile', username=username, email=email))
            else:
                message = "Invalid email or password"
                if request.is_json:
                    return jsonify({"error": message}), 401
                return render_template('signin.html', error=message)

        except Exception as e:
            message = str(e)
            if request.is_json:
                return jsonify({"error": message}), 500
            return render_template('signin.html', error=message)

    return render_template('signin.html')

@app.route('/profile')
def profile():
    username = request.args.get('username')
    email = request.args.get('email')
    return render_template('profile.html', username=username, email=email)

@app.route('/logout')
def logout():
    return redirect(url_for('signin'))


@app.route('/comingsoon')
def comingsoon():
    return render_template('comingsoon.html')


if __name__ == '__main__':
    app.run(debug=True)
