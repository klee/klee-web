FROM postgres:9.5-alpine

# bring in environmental variables
# copy config
# copy the other config files
# ARG DATABASE_NAME
# ARG USER
# ARG PASSWORD

# ENV DATABASE_NAME=POSTGRES_DB
# ENV POSTGRES_USER=USER
# ENV POSTGRES_PASSWORD=PASSWORD

COPY ./postgresql.conf postgres.conf
COPY ./pg_hba.conf /etc/postgresql/9.5/main/pg_hba.conf
COPY ./pgdg.list /etc/apt/sources/list.d/pgdg.list

CMD ["postgres"]