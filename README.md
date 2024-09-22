### Backend for CuiiListe.de

If you want to run this yourself, please set up a MariaDB database with the 
tables described in the `database.py` file.

You will need the following environment variables:
```dotenv
DB_HOST=127.0.0.1
DB_USER=myUser
DB_PASS=SecurePassword
DB_NAME=cuii
WEBHOOK_URL=https://discord.com/api/webhooks/1234567890986/SOMETHING
CUII_NOTIF_ROLE_ID=1234567890986
```

You will need to insert DNS servers into your database manually. 
Sadly, ISPs don't allow access to their DNS servers from outside, a rare exception is telekom.
You can get their public DNS servers by running
```bash
dig @dns00.dns.t-ipnet.de +short $(python3 -c 'print("dns.telekom.de "*20)') | sort | uniq
```
If you have any questions, feel free to ask me on 
Matrix, Discord, Email or really wherever you want. 
You can find my contact information on my website: [damcraft.de](https://damcraft.de)