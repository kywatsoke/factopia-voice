FACTOPIA VOICE 2.0 - offline voiceover studio

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
  Library        Every clip you made, with its script. Play, download, reuse.
  Pronunciation  Fix how a word is said once; it is applied to every clip after.
  Settings       Target length, folders, and Quit.

YOUR FILES
  Everything you create is in the "data" folder next to this file:
    data/output           your audio clips
    data/profile.json     voice, speed, pause, file type
    data/dictionary.json  pronunciation fixes
    data/library.json     clip history
  To update the app later, replace everything except the "data" folder.

CHANGE THE VOICE
  Version 2.0 uses one voice. To try another, quit the app, open
  data/profile.json and change "voice" (for example am_fenrir, am_puck,
  af_heart, bm_george), then start again.

NEEDS
  A Mac or Windows PC from the last several years, about 2 GB of free memory
  and 1 GB of disk. No graphics card needed.

QUIT
  Settings > Quit Factopia Voice, or close the terminal window.
