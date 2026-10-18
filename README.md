# Team Overclock: Senior Project
 
A web dashboard for assigning, submitting, and reviewing intern work. Approved submissions earn points and are credited on the intern's record of completed work.
 
CSC 190/191 Senior Project, Sacramento State, Fall 2026 to Spring 2027
Team Overclock · Client: The Emerson Empire · Advisor: Kenneth Elliott
 
> **Status:** Sprint 0. Product name, stack, and specifications not final.
 
## Overview
 
The client's founder currently assigns, tracks, and reviews all intern work by hand in an Excel spreadsheet. This project replaces it: supervisors post assignments, interns submit work in one place, reviewers approve or request changes, and approved work adds to a points ledger and a page listing the intern's approved work.
 
## Features
 
**Must-have:** sign-in with roles (member, supervisor, admin), assignments, intern dashboard, submissions, review with feedback, points ledger and approved-work page, notifications, hosted deployment.
 
**CSC 191:** AI review assistant that drafts a score and feedback for the reviewer. It never approves work or awards points.
 
**Nice-to-have:** Excel import, GitHub/Discord/Slack/calendar integrations, client access, analytics.
 
## Tech stack
 
TBD
 
## Architecture
 
TBD
 
## Getting started
 
You need [Docker Desktop](https://www.docker.com/products/docker-desktop)
and [Git](https://git-scm.com). Nothing else.

1. Clone the repository and go into it:
   `git clone https://github.com/dschell3/Byline.git && cd Byline`
2. Create your local settings file from the template:
   `cp .env.example .env` (the defaults work as they are)
3. Start everything:
   `docker compose up`
   The first run takes a few minutes while it downloads and builds.
4. Open http://localhost:5173 for the app and
   http://localhost:8000/docs for the API.

`Ctrl+C` stops it. `docker compose down -v` wipes the database for a fresh
start. To run the API or front end without Docker, see `api/README.md` and
`web/README.md`.
 
## Contributing
 
TBD
 
## Testing
 
TBD
 
## Deployment
 
TBD
 
## Team
 
| Name | Role | GitHub |
| --- | --- | --- |
| Jangbahadar Singh | Team lead | |
| Darren Schell | AI and backend | [dschell3](https://github.com/dschell3) |
| | | |
 
## Links
 
[Jira](https://csus-team-notchuds.atlassian.net/jira/software/projects/SCRUM/boards/1) · Figma · Project website · Charter (Figma, website and charter TBD)
 
## License
 
TBD