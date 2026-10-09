# Roadmap

The live plan, with the backlog and its status, is the
[Factopia Voice Project Plan](https://claude.ai/code/artifact/386ec8c1-7405-436d-b044-ff9045de0579).
This file is a snapshot of it for the repository, taken 9 October 2026.

## Releases

| Release | Contains | Ships when | Status |
| --- | --- | --- | --- |
| 2.0 Voice | Script to voiceover, pronunciation dictionary, clip library | Runs on the Mac from a clean folder | Done (Mac, 7 Oct 2026) |
| 2.1 Captions | Speech to text, caption editor, styling, SRT and burned-in export | A 60-second video is captioned and exported in one sitting | Done (Mac, 7 Oct 2026) |
| 2.2 Translate | English, Chinese and Burmese in every direction; caption translation; SRT import | Real translations run on the Mac and the Burmese and Chinese are judged good enough | Built; real-model test pending |
| Later: Reader | On-screen caption reader (OCR) | When wanted | Postponed |
| 3.0 Public beta | Installer, signed builds, updates, licence notices | Only if the app is to be sold | Not planned yet |

## Backlog

| Item | Release | Status |
| --- | --- | --- |
| Run on Windows | 2.0 to 2.2 | Open: the tests run on Windows in CI; nobody has used it there yet |
| Real-model translation test on the Mac | 2.2 | Open |
| Burmese burned-in captions on Mac and Windows: supply FriBiDi so Pillow can shape Burmese (LGPL, loaded at run time) | 2.2.x | Next: found by CI on 9 Oct 2026; SRT export works meanwhile |
| Judge Burmese and Chinese output; choose 4B or 12B | 2.2 | Open |
| Voice tone improvement (rated about 60%) | Next | Not started |
| Rename the app (it is more than a voice now) | Next | Not started |
| Voice picker and more voices (Kokoro has 54) | Later | Later |
| Burmese voice | Later | No commercially usable offline voice found |
| Short assembler: voiceover, clips and captions into one vertical video | Later | Later |
| Footage library with a licence log (Pexels, Pixabay, NASA) | Later | Later |
| Channel tracker on YouTube's analytics API | Later | Later |
| Phone access over Wi-Fi, behind a PIN | Later | Later |
| Replace the GPL text-to-phoneme step | 3.0 | Only for a closed-source release |
| Installer and signed builds | 3.0 | Only if going public |

## How a release is made

Every release goes through the same six steps. Each has a check that must
pass before the next starts.

1. **Define.** One paragraph on what the release does and a short list of
   acceptance checks. Check: the owner agrees the list.
2. **Spike.** Try the engine on a real sample; measure speed, memory and
   accuracy; confirm its licence. Check: numbers recorded in
   [DECISIONS.md](DECISIONS.md), licence allows the intended use.
3. **Build.** Implement behind the existing interfaces, with automated tests
   for the rules. Check: tests pass on all three platforms in CI.
4. **Verify.** Run the release zip from a clean folder on macOS and Windows,
   first-time setup included ([TESTING.md](TESTING.md)). Check: both complete
   the acceptance list.
5. **Release.** Changelog entry, licence register updated, version tag
   ([DEVELOPMENT.md](DEVELOPMENT.md)). Check: an older data folder opens
   unchanged.
6. **Use and review.** Use it on real videos for a week and log every
   problem as a GitHub issue. Check: issues sorted into the backlog before
   the next release starts.
