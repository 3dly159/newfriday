# SeelSupport Setup for Friday

Friday's SeelSupport tools work once you connect your SeelSupport credentials. One-time setup:

1. Create a configuration file named `config/seelsupport_creds.json` under the project root.
2. Put the following format in the file:
```json
{
  "phone": "YOUR_PHONE_NUMBER",
  "password": "YOUR_PASSWORD"
}
```
3. Friday will automatically use these credentials to authenticate against `https://seelsupport.unaux.com/api/login`, solve the DDoS challenge, acquire a Bearer token, and perform any CRUD operations or check for new notifications.

Until then, every SeelSupport tool simply replies that SeelSupport isn't configured — nothing breaks.
