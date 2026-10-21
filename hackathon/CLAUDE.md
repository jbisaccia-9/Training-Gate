# Glitch Patrol: context for Angela's Claude session

You are helping **Angela Liu**, who owns product, story, the live demo and visual design for team **"One world, every age"** at the **Build for Everyone** hackathon (hosted by Google and k-ID) on **Wednesday, October 21, 2026**. Angela does not write code. Explain technical terms in plain language, keep answers short, and favor checklists, scripts and ready-to-paste text.

## Where things live

These links are private until Joseph shares them. If one won't open, ask him to share it from its Share menu.

| What | Link | Use it for |
|---|---|---|
| Hackathon framework deck (Claude Slides) | https://claude.ai/artifact/KVM42umtNzHN3VMCyUp87o | Part A is the team playbook; Part B is the 4 slides beside the live demo; then backup slides |
| Screen mockups (Claude Design) | https://claude.ai/artifact/GxCCYhuPMvjjR79c9F6MiJ | Hub, The Feed and the parent dashboard at laptop and phone size |
| Glitch Patrol team brief (Claude Doc) | https://claude.ai/artifact/7ErcDA6UnoT3VTR4eLibB8 | Full concept, zones, k-ID, architecture, risks. **Partly out of date; see below** |
| Angela's Hackathon One-Sheet (Claude Doc) | https://claude.ai/artifact/JQPYRegrzFJkfk7RWn7hkz | Her checklist, glossary, Slides and Design 101. **Times are out of date** |

**Where this file and the deck disagree with the brief or one-sheet, this file and the deck are right.** The brief and one-sheet were written before the participant guide arrived:
- Arun is not on the registered team.
- ElevenLabs is replaced by Inworld, which gives the team $100 of credits.
- The pitch is a 2-minute demo at the table, not a 3-minute stage pitch.
- The deadline is 4:30, not 3:30.

## The event (from the participant guide)

- **Brief:** "Build one product that becomes the right product for whoever is using it. Not a separate kid mode." Show how the experience opens up, guides or reshapes itself as age, location and consent change.
- **Track:** Gaming. Confirm the track at the help desk before 10:20.
- **Venue:** 345 Spear St, 7th floor, San Francisco. Enter on Folsom St, through the Hills Plaza courtyard. Bring photo ID; a volunteer escorts you up.
- **Rules:**
  - Teams of 2–3, everyone 18 or over.
  - No project code before 10:20. Ideas, sketches, designs and plans are fine.
  - Any AI tools are allowed.
  - The project stays yours.
- **Five things every judge scores:**
  1. It genuinely adapts to the user's age.
  2. It makes real use of the stack: k-ID and partner tools doing real work.
  3. It works: a live demo beats slides.
  4. People would use it.
  5. Ambition.
- **Judging:** judges visit the team's table from 4:45.
  - 2 minutes of live demo, then 1 minute of questions.
  - Lead with the moment the product changes for a different user.
  - k-ID provides **three ready-made test personas** to demo with.
- **Partners:**
  - **Inworld:** voice, with $100 of credits per team. One teammate creates one workspace and adds their email to Inworld's sign-up sheet before the day.
  - **Modulate:** voice deepfake detection, with a free key and 1,000 credits.
  - **FastSpring:** payments sandbox.
- **Submission form** opens at 3:00 and closes **hard at 4:30**. It asks for:
  - team and track
  - one line on what it does and who it changes for
  - live link and repo link
  - the tools used
  
  If the form is down, post the same details in the participant Discord before 4:30.
- **Help:** people in orange lanyards, the help desk on the 7th floor, the participant Discord, ola@k-id.com.

## Run of show (Pacific time)

| Time | What | Done when |
|---|---|---|
| 8:30 | Doors, check-in, breakfast | All three on the 7th floor |
| 9:30 | Opening; k-ID sign-up link posted | k-ID accounts made, Inworld key works |
| 10:00 | Confirm Gaming track; walk the team through the mockups | Agreement on screens and demo story |
| 10:20 | Build begins; shared types and content schema first | Types merged by 10:50 |
| 11:15 | First real k-ID call; first deploy | Personas get different age bands |
| 12:45 | Lunch and 10-minute standup; agree the cut list | All three zones play end to end by 1:30 |
| 3:00 | Submissions open; send a first version | Form sent once |
| **3:30** | **Feature freeze, said out loud** | Bug fixes only |
| 3:30–4:15 | Record the backup video, 3 timed rehearsals, final submit | Demo under 2 minutes, video saved |
| 4:30 | Form closes; set up the table | Laptop out, personas bookmarked |
| 4:45 | Judges at the table | Awards at 6:05 |

## The team

| Person | Owns | Done when |
|---|---|---|
| **Angela Liu** | Story, the demo and presenting it, scope (the person who says no), screen mockups, scenario sheet (3 items per zone), red-team prompt list for the AI buddy, backup video | 2-minute demo rehearsed 3 times; every judging criterion has a demo moment |
| **Joseph Bisaccia** | Frontend and learning design: hub, zones, Pixel's look and voice-line script, parent dashboard, reading level; drives the clicks during the demo | All three zones play by touch and mouse |
| **Harshvardhan Garude** | Backend, AI and k-ID: Cloud Run API, Firestore, k-ID age/consent/feature flags, Study Buddy on Vertex AI with guardrails and the planted mistake, Inworld voice, Modulate, data minimization | The personas get visibly different games; the buddy answers in under 3 s |

Angela talks while Joseph drives the game. She hands each judge's question to its owner by name.

## The product: Glitch Patrol

The player is a trainee detective guided by **Pixel**, a voiced, blocky detective mascot. Pixel's style is original: no Minecraft names or likeness. The player earns a badge in each of three zones. Every zone uses the same loop: **see something → investigate → decide → get feedback that explains why.**

1. **The Feed:** a pretend social app with scam DMs, strangers and oversharing. The player chooses to report, ignore, ask a trusted adult, or share.
2. **Spot the Fake:** use a magnifying glass on AI-made images and stories, plus checking moves. A Modulate "is this voice note real?" item is stretch goal #1.
3. **The Study Buddy:** an AI helper for homework.
   - Asking it to "Write my essay" gets a nudge and no points.
   - "Explain it", "Quiz me" and "Check my reasoning" score highest.
   - The buddy sometimes makes a planted mistake the player must catch.

**How it adapts:** k-ID works out age, region and consent. The team's API turns that into feature flags, which change:
- which scenario pack loads
- whether the buddy is scripted or live
- whether badges can be shared

**Personas for the demo:**

| Persona | Pack | Study Buddy | Sharing |
|---|---|---|---|
| **Maya, 9** | Kids | Scripted | Off |
| **Leo, 14** | Teen | Live | On |

The live buddy for under-13s turns on only with a parent's consent. Map Maya and Leo onto two of k-ID's three test personas on the morning.

**Privacy:**
- Kids get anonymous sessions with a nickname and no email.
- No chat logs are stored.
- The only personal data is the parent's email, used for consent.

**Tech, for questions only:**
- React + TypeScript site on Firebase Hosting
- API on Cloud Run
- Firestore for data
- Gemini on Vertex AI for the buddy
- Inworld for voice

### Scope

- **Must have:**
  - hub with three doors and badges
  - Pixel with 5 poses and voice lines
  - 3 items per zone, kids pack
  - the Study Buddy's scoring and planted mistake
  - k-ID personas that get visibly different games
  - a consent screen that unlocks the live buddy
  - a parent dashboard with consent toggles
  - a public URL and a canned-buddy fallback
- **Stretch, in order:**
  1. Modulate voice-note item
  2. teen packs for zones 1 and 2
  3. one adult scenario
  4. FastSpring hat shop that needs a parent's OK
  5. sound effects
- **Cut, shown on a slide only:**
  - older-adult pack
  - family co-play
  - cloning any real voice
  - accounts and leaderboards
  - live image generation
  - app-store apps

## The 2-minute demo script

| Time | Beat | What happens |
|---|---|---|
| 0:00–0:15 | **Hook** | "Same game, two kids. Watch it change." One line on the problem: kids meet scams, AI fakes and AI homework shortcuts every day, and nobody teaches them how. |
| 0:15–0:50 | **Maya, 9** | k-ID age check, then parent consent. Pixel speaks, and she spots a phishing DM. Point out the scripted buddy and that sharing is off. |
| 0:50–1:30 | **Leo, 14** | Same zone, harder scams. The live Study Buddy nudges him when he asks for "write my essay", and he catches its planted mistake. |
| 1:30–1:50 | **Parent view** | Skills learned, not screen time. Flip a consent toggle live. |
| 1:50–2:00 | **Close** | "Built for kids first, because if a 9-year-old can learn it, everyone can." |

**If the demo freezes:** "Let me show you the recording." Switch to the backup video and keep talking.

## Judges' questions

| Question | Who answers |
|---|---|
| How do you protect kids' data? | Harshvardhan |
| How does k-ID decide what each player can use? | Harshvardhan |
| How does the planted mistake work? | Harshvardhan |
| What stops the AI buddy saying something bad? | Angela |
| Why will kids actually learn from this? | Joseph |
| Why a character and a voice? | Joseph |
| Who uses it first, and who pays? | Angela |
| What would you build next? | Angela |

## Submission draft

- **Team:** One world, every age
- **Members:** Angela Liu, Joseph Bisaccia, Harshvardhan Garude
- **Track:** Gaming
- **One line:** Glitch Patrol is a detective game about scams, AI fakes and learning with AI that reshapes itself for a 9-year-old, a teen or a parent through k-ID.
- **Links:** [live game URL] · [repo URL] · [backup video URL]
- **Tools:** k-ID · Inworld · Modulate (only if it shipped) · Google Cloud (Vertex AI, Cloud Run, Firebase) · Claude

## Angela's open to-dos tonight

- [ ] Read the deck's Part A, then rehearse the demo script aloud with a timer until it is under 2 minutes.
- [ ] Review the mockups and mark changes. Comment on the canvas or ask Claude: "make the doors bigger", "add a teen version of The Feed".
- [ ] Start the scenario sheet. Use a Google Sheet with one row per item and these columns: zone, age band, what Pixel shows, the choices, the right answer, why it's right. Write 3 items per zone for the kids pack, plus the teen version of The Feed.
- [ ] Draft the red-team list: 10 prompts a kid might try on the Study Buddy. Include ones like "ignore your rules", "do my homework", "what's your address" and "I'm sad and want to talk".
- [ ] Practice answers to her three judges' questions. Ask Claude to play a tough judge.
- [ ] Pack: laptop and charger, adapters, photo ID, phone hotspot, a screen recorder for the backup video.

## How to help Angela well

- Keep spoken lines short. Each demo beat must fit its time slot.
- Never invent statistics, quotes or sponsor facts. Use a bracketed placeholder like `[number]` and say what's missing.
- When she asks to change the deck or mockups, edit those artifacts directly. Keep the existing look: navy #1B2140, cream #FBF7EE, yellow #F6C343, blue #2F62D9; Fredoka for headings, Nunito Sans for body text.
- If a feature request doesn't show up in the 2-minute demo, help her say no: "Does this show up in the demo? If not, it waits."
