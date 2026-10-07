FACTOPIA VOICE 2.1 - offline voiceover and captions studio

START
  Mac:      double-click "Start Factopia Voice (Mac).command"
            (first time: right-click it, choose Open, then Open again)
  Windows:  double-click "Start Factopia Voice (Windows).bat"
            (if Windows shows a blue warning: More info, then Run anyway)

  The first start needs internet and a few minutes. It sets up Python and
  downloads the voice model (about 340 MB). After that it works offline.
  The app opens in its own window if Chrome or Edge is installed, otherwise
  in your default browser.

USE
  Studio         Paste a script, press Generate voiceover (or Ctrl/Cmd + Enter).
                 A blank line adds a pause. [pause 0.8] adds an exact pause.
  Captions       Import a video or audio file, or press Captions on a Library
                 clip. English speech becomes timed lines. Fix the text and
                 timing, pick a font and style, then export a subtitle file
                 (SRT) or a copy of the video with the captions burned in.
                 The first use downloads a speech model of about 460 MB.
  Library        Every clip you made, with its script. Play, download, reuse.
  Pronunciation  Fix how a word is said once; it is applied to every clip after.
  Settings       Target length, folders, and Quit.

YOUR FILES
  Everything you create is in the "data" folder next to this file:
    data/output           your audio clips, subtitle files and captioned videos
    data/projects         imported files and their captions
    data/profile.json     voice, speed, pause, file type
    data/dictionary.json  pronunciation fixes
    data/library.json     clip history
  To update the app later, replace everything except the "data" folder.

CHANGE THE VOICE
  This version uses one voice. To try another, quit the app, open
  data/profile.json and change "voice" (for example am_fenrir, am_puck,
  af_heart, bm_george), then start again.

NEEDS
  A Mac or Windows PC from the last several years, about 3 GB of free memory
  and 2 GB of disk. No graphics card needed.

QUIT
  Settings > Quit Factopia Voice, or close the terminal window.

FOR DEVELOPMENT
  Run the tests:
    uv run --python 3.12 --no-project --with-requirements requirements.txt \
       --with-requirements requirements-dev.txt pytest -q
  See CHANGELOG.md for what changed and LICENSES.md for third-party licences.
