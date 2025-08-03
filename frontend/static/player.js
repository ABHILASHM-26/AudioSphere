
function initializePlayer() {
    const playbackState = JSON.parse(localStorage.getItem('playbackState'));
    if (playbackState) {
        const audioPlayer = document.getElementById('audioPlayer');
        const songName = document.getElementById('song-name');
        const artistName = document.getElementById('artist-name');
        const songPhoto = document.getElementById('song-photo');

        if (audioPlayer) {
            audioPlayer.src = playbackState.currentSong;
            audioPlayer.currentTime = playbackState.currentTime || 0;
        }
        if (songName && playbackState.songName) {
            songName.textContent = playbackState.songName;
        }
        if (artistName && playbackState.artistName) {
            artistName.textContent = playbackState.artistName;
        }
        if (songPhoto && playbackState.photoURL) {
            songPhoto.src = playbackState.photoURL;
        }
    }
}

function handlePageTransition() {
    window.addEventListener('beforeunload', function () {
        const audioPlayer = document.getElementById('audioPlayer');
        const songName = document.getElementById('song-name')?.textContent || "";
        const artistName = document.getElementById('artist-name')?.textContent || "";
        const photoURL = document.getElementById('song-photo')?.src || "";

        if (audioPlayer) {
            const playbackState = {
                currentSong: audioPlayer.src,
                currentTime: audioPlayer.currentTime,
                songName,
                artistName,
                photoURL
            };
            localStorage.setItem('playbackState', JSON.stringify(playbackState));
        }
    });
}

function startPlayback(songURL, name, artist, photoURL) {
    const audioPlayer = document.getElementById('audioPlayer');
    const songName = document.getElementById('song-name');
    const artistName = document.getElementById('artist-name');
    const songPhoto = document.getElementById('song-photo');

    if (audioPlayer && songURL) {
        audioPlayer.src = songURL;
        audioPlayer.play().catch(error => console.error("Playback failed:", error));
    }

    if (songName) songName.textContent = name;
    if (artistName) artistName.textContent = artist;
    if (songPhoto) songPhoto.src = photoURL;

    const playbackState = {
        currentSong: songURL,
        currentTime: 0,
        songName: name,
        artistName: artist,
        photoURL: photoURL
    };
    localStorage.setItem('playbackState', JSON.stringify(playbackState));
}


window.addEventListener('load', function () {
    initializePlayer();
    handlePageTransition();

    const playButton = document.getElementById("playsong");
    if (playButton) {
        playButton.addEventListener("click", function () {
            const audio = document.getElementById("audioPlayer");
            if (audio) {
                audio.play().catch(error => console.error("Play failed:", error));
            }
        });
    }
});

window.startPlayback = startPlayback;
