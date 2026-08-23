# Health Coaching Client Management App

A self-contained Flask + SQLite application for a health-coaching business in India.

## Included
- Admin-only dashboard and client database
- Professional public intake form link
- MCQs, select-all-that-apply, ratings, text/long answers
- "Other" option with free text for applicable lists
- Daily schedule and food-preference intake
- Health/lifestyle intake fields
- Individual client profiles
- Intake submissions stored under each client
- Weight and measurement history, including custom measurements
- PDF/image/document uploads and private client file storage
- Diet-plan upload category
- Payment tracking
- Text/video feedback
- Mobile-friendly design
- Password hashing, CSRF tokens on admin forms, secure random stored filenames, upload allow-list, security headers and private file routes

## Run locally
Python 3.11+ recommended.

macOS/Linux:
    ./run.sh

Windows:
    run.bat

Then open http://127.0.0.1:5000

Default demo password is only for first local setup. Set HC_ADMIN_PASSWORD to a strong unique password before using real data.

## Production warning
This is a functional application build, not a certification that a deployment is immune to hacking or bugs. For real client health information, deploy with HTTPS, MFA, managed private database/object storage, encrypted backups, monitoring, rate limiting, dependency patching, audit logging, least privilege, secure secrets, disaster recovery, and an India-specific privacy/legal review. Never use the demo/default password.
