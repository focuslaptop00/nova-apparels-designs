# Meesho Product Review Hub (3 Partners)

A lightweight web app for Meesho sellers and remote partners to review 40-50 product designs without WhatsApp confusion.

## Features:
1. **Zero Login Friction:** Asks partner name once on 1st visit (Harsh / Partner 2 / Partner 3) and remembers it permanently.
2. **Reviewer Attribution:** Every status change and comment clearly shows who wrote it.
3. **Threaded Discussion & Replies:** Any partner can reply to any other partner's comment directly.
4. **Bulk Image Upload:** Upload 40-50 photos in 1 click.
5. **Quick Issue Tags:** 1-tap buttons for Fabric Issue, Color/Print blur, Price high, etc.
6. **WhatsApp Summary:** 1-click copies the final report of Approved, Cancelled, and Issue designs for WhatsApp.
7. **Real-time Live Sync:** Auto-updates every 4 seconds.

## How to run locally:
```bash
./run.sh
# Open http://localhost:8080 in browser
```

## How to get a live link for remote partners:
```bash
ssh -p 443 -R0:localhost:8080 qr@a.pinggy.io
```
(Or use Render / Railway for permanent 24/7 cloud hosting).
