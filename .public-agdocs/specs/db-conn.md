setup an async connection to postgres db that can be configured with .env (add relevant lines to .env.example as nec.)
- DB_HOST: 127.0.0.1
- DB_PASSWORD: demopassword
- DB_PORT: 5433
- DB_NAME: p1db_1
log db conn success or failure.

create a data model for the shapes data structure that gets used in the database.

create a script on the side that seeds the DB with the data hard-coded in /shapes route currently.

pull the data from the shapes table into the shapes route (instead of the hard-coded data).