# Steam-Price-Tracker
Flask/Python based app that will allow you to scrape Steam prices and will send you an email if the price changes.

## Why this project?

This project was done to conicide with the 100th day of Replit's 100 Days of Code. The final project was a little too basic for my tastes. I've tried to push myself as much as possible to maximize my amount of learning while doing this project.

### Features:

- Login System with hashed/salted passwords stored in the Replit Database
- Password Recovery System
- Email Confirmation
- Token Generation and verification system for Password Recovery/Email Confirmation
- CSRF Protection
- Ability to add games to a Price Tracking List
- Set Price Target
- Page will scrape the Steam website to get price updates, email sent if price is below price target
- Admin panel to view user information/delete users
- Background scheduler to update prices/purge old tokens
- Supports bundles and games that aren't for sale yet. Will email you when they go on sale.

### Status

It does the job it is supposed to do. It no doubt has some bugs here and there. It also isn't the prettiest website ever but my main focus was on the backend and not the frontend. That being said, I did take the opportunity to practice HTML/CSS whenever possible here.
